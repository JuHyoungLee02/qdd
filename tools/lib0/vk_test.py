"""E-SIM0 setup: where does SAPIEN 2.2.2 stall headless? faulthandler dumps the stack every 60 s."""
import faulthandler
import sys
import time

faulthandler.dump_traceback_later(60, repeat=True, file=sys.stderr)
t0 = time.time()
import sapien.core as sapien
print("import", round(time.time() - t0, 1), flush=True)
import os
if os.environ.get("SHADER"):
    sapien.render_config.camera_shader_dir = os.environ["SHADER"]
    sapien.render_config.viewer_shader_dir = os.environ["SHADER"]
eng = sapien.Engine()
print("engine", round(time.time() - t0, 1), flush=True)
r = sapien.SapienRenderer(offscreen_only=True)
print("renderer", round(time.time() - t0, 1), flush=True)
eng.set_renderer(r)
sc = eng.create_scene()
print("scene", flush=True)
cam = sc.add_camera("c", 64, 64, 1.0, 0.01, 10)
print("camera", flush=True)
sc.step(); sc.update_render(); print("updated", flush=True); cam.take_picture()
print("picture", cam.get_float_texture("Color").shape, round(time.time() - t0, 1), flush=True)
