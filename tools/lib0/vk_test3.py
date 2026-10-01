"""E-SIM0 setup: SAPIEN 3 headless render test (does the 580 driver + Vulkan work with SAPIEN 3?)."""
import time

t0 = time.time()
import sapien
print("import", sapien.__version__, round(time.time() - t0, 1), flush=True)
sc = sapien.Scene()
cam = sc.add_camera("c", 64, 64, 1.0, 0.01, 10)
print("camera", flush=True)
sc.step(); sc.update_render(); cam.take_picture()
print("picture", cam.get_picture("Color").shape, round(time.time() - t0, 1), flush=True)
