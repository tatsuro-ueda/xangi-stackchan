from pathlib import Path

Import("env")


HOOK_DECL = 'extern "C" void xangi_avatar_overlay(M5Canvas* sprite) __attribute__((weak));'
HOOK_CALL = """  if (xangi_avatar_overlay) {
    xangi_avatar_overlay(sprite);
  }
"""


def patch_avatar_face(*_args, **_kwargs):
    project_dir = Path(env.subst("$PROJECT_DIR"))
    face_cpp = project_dir / ".pio/libdeps/cores3-main/M5Stack-Avatar/src/Face.cpp"
    if not face_cpp.exists():
        print(f"[patch_m5stack_avatar] skip: {face_cpp} not found")
        return

    text = face_cpp.read_text(encoding="utf-8")
    changed = False

    if HOOK_DECL not in text:
        include_anchor = '#include "Face.h"\n'
        if include_anchor not in text:
            raise RuntimeError("[patch_m5stack_avatar] Face.cpp include anchor not found")
        text = text.replace(
            include_anchor,
            include_anchor + "\n" + HOOK_DECL + "\n",
            1,
        )
        changed = True

    if "xangi_avatar_overlay(sprite);" not in text:
        anchor = "  battery->draw(sprite, br, ctx);\n  // drawAccessory(sprite, position, ctx);\n"
        if anchor not in text:
            raise RuntimeError("[patch_m5stack_avatar] Face.cpp draw anchor not found")
        text = text.replace(
            anchor,
            "  battery->draw(sprite, br, ctx);\n" + HOOK_CALL + "  // drawAccessory(sprite, position, ctx);\n",
            1,
        )
        changed = True

    if changed:
        face_cpp.write_text(text, encoding="utf-8")
        print("[patch_m5stack_avatar] patched M5Stack-Avatar Face.cpp")


patch_avatar_face()
env.AddPreAction("buildprog", patch_avatar_face)
