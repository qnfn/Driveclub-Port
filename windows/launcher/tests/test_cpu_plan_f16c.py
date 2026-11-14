# SPDX-License-Identifier: GPL-2.0-or-later
"""F16C translations (prepare/cpu_plan.py, issue #15): DRIVECLUB's half-float helpers use
VCVTPS2PH/VCVTPH2PS, which Intel CPUs before Ivy Bridge lack. Each translation runs here next to
the real instruction and must give the same bits, registers and flags."""
import os
import random
import struct

import pytest

import dcport.prepare_state  # noqa: F401  (puts prepare/ on sys.path)

cpu_plan = pytest.importorskip("cpu_plan")


def test_memory_and_ymm_forms_are_left_unhandled():
    for mnemonic, operands in (("vcvtps2ph", "qword ptr [rax], xmm0, 0"),
                               ("vcvtph2ps", "ymm0, xmm1"), ("vcvtps2ph", "xmm0, xmm0, 1")):
        with pytest.raises(ValueError):
            cpu_plan.f16c_body(mnemonic, operands)


def _native(code: bytes):
    import ctypes
    k32 = ctypes.WinDLL("kernel32")
    k32.VirtualAlloc.restype = ctypes.c_void_p
    k32.VirtualAlloc.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32)
    memory = k32.VirtualAlloc(None, len(code), 0x3000, 0x40)
    ctypes.memmove(memory, code, len(code))
    return ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(memory)


def _harness(core: bytes):
    """f(in, out): xmm3 = 16 bytes at in, ymm5 all ones, known rax..r9 and flags, then `core`;
    out = ymm5, rax, rcx, rdx, r8, r9, flags after, flags before."""
    asm = cpu_plan.ASSEMBLER
    pre = asm.asm("push rbx; push r12; mov r10, rdx; vmovdqu xmm3, xmmword ptr [rcx];"
                  "vpcmpeqd ymm5, ymm5, ymm5; mov rax, 0x1111111111111111;"
                  "mov rcx, 0x2222222222222222; mov rdx, 0x3333333333333333;"
                  "mov r8, 0x4444444444444444; mov r9, 0x5555555555555555;"
                  "mov ebx, 5; cmp ebx, 7; pushfq; pop r12")[0]
    post = asm.asm("pushfq; pop rbx; vmovdqu ymmword ptr [r10], ymm5; mov [r10+32], rax;"
                   "mov [r10+40], rcx; mov [r10+48], rdx; mov [r10+56], r8; mov [r10+64], r9;"
                   "mov [r10+72], rbx; mov [r10+80], r12; vzeroupper; pop r12; pop rbx; ret")[0]
    return _native(bytes(pre) + core + bytes(post))


def _has_f16c() -> bool:
    import cpu_compat
    return cpu_compat.missing_host_extensions() is not None and \
        "F16C" not in cpu_compat.missing_host_extensions()


@pytest.mark.skipif(os.name != "nt", reason="runs machine code (Windows)")
@pytest.mark.parametrize("mnemonic, operands", [("vcvtps2ph", "xmm5, xmm3, 0"),
                                                ("vcvtph2ps", "xmm5, xmm3")])
def test_translation_matches_the_instruction(mnemonic, operands):
    import ctypes
    if not _has_f16c():
        pytest.skip("this CPU has no F16C to compare with")
    ours = _harness(cpu_plan.body(mnemonic, operands))
    real = _harness(bytes(cpu_plan.ASSEMBLER.asm(f"{mnemonic} {operands}")[0]))
    if mnemonic == "vcvtps2ph":
        rng = random.Random(15)
        values = [0, 0x80000000, 0x7f800000, 0xff800000, 0x7fc00001, 0x7f800001, 0x477ff000,
                  0x477fefff, 0x38800000, 0x387fffff, 0x33000000, 0x33000001, 0x33800000, 1,
                  0x007fffff, 0x3f801000, 0x3f803000, 0x3f802fff]
        values += [rng.getrandbits(32) for _ in range(40000)]
        values += list(range(0x32000000, 0x39000000, 0x1fff))
        pack = "<4I"
    else:
        values, pack = list(range(0x10000)), "<4H8x"
    source = ctypes.create_string_buffer(16)
    a, b = ctypes.create_string_buffer(88), ctypes.create_string_buffer(88)
    for i in range(0, len(values), 4):
        lanes = (values[i:i + 4] + [0] * 4)[:4]
        ctypes.memmove(source, struct.pack(pack, *lanes), 16)
        ours(source, a)
        real(source, b)
        assert a.raw == b.raw, [hex(v) for v in lanes]
