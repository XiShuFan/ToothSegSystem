import vedo
import numpy as np

mesh = vedo.load('2.ply')
points = np.array(mesh.points())

# 每个维度坐标均值
print(np.mean(points, axis=0, keepdims=True))
# 包围盒大小
print('min', np.min(points, axis=0, keepdims=True))
print('max', np.max(points, axis=0, keepdims=True))

mesh = vedo.load('4.ply')
points = np.array(mesh.points())

# 每个维度坐标均值
print(np.mean(points, axis=0, keepdims=True))
# 包围盒大小
print('min', np.min(points, axis=0, keepdims=True))
print('max', np.max(points, axis=0, keepdims=True))

mesh = vedo.load('16.ply')
points = np.array(mesh.points())

# 每个维度坐标均值
print(np.mean(points, axis=0, keepdims=True))
# 包围盒大小
print('min', np.min(points, axis=0, keepdims=True))
print('max', np.max(points, axis=0, keepdims=True))

mesh = vedo.load('0140W3ND_lower.obj')
points = np.array(mesh.points())

# 每个维度坐标均值
print(np.mean(points, axis=0, keepdims=True))
# 包围盒大小
print('min', np.min(points, axis=0, keepdims=True))
print('max', np.max(points, axis=0, keepdims=True))

mesh = vedo.load('0140W3ND_lower.ply')
points = np.array(mesh.points())

# 每个维度坐标均值
print(np.mean(points, axis=0, keepdims=True))
# 包围盒大小
print('min', np.min(points, axis=0, keepdims=True))
print('max', np.max(points, axis=0, keepdims=True))