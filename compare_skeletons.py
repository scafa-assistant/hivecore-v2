"""Vergleicht Ruhepose zwischen confused.glb und idle_natural.glb"""
import struct, math
from pygltflib import GLTF2

def euler(q):
    x,y,z,w = q
    m11=1-2*(y*y+z*z); m12=2*(x*y-w*z); m13=2*(x*z+w*y)
    m22=1-2*(x*x+z*z); m23=2*(y*z-w*x); m32=2*(y*z+w*x); m33=1-2*(x*x+y*y)
    ry=math.asin(max(-1,min(1,m13)))
    if abs(m13)<0.9999999: rx=math.atan2(-m23,m33); rz=math.atan2(-m12,m11)
    else: rx=math.atan2(m32,m22); rz=0
    return (math.degrees(rx),math.degrees(ry),math.degrees(rz))

def read_acc(gltf,idx):
    acc=gltf.accessors[idx]; bv=gltf.bufferViews[acc.bufferView]
    blob=gltf.binary_blob(); off=(bv.byteOffset or 0)+(acc.byteOffset or 0)
    nc={'SCALAR':1,'VEC4':4}[acc.type]
    fmt=f'<{acc.count*nc}f'
    data=struct.unpack(fmt,blob[off:off+struct.calcsize(fmt)])
    return [data[i:i+nc] for i in range(0,len(data),nc)] if nc>1 else list(data)

BONES = {'Head':'head','neck':'neck','RightArm':'upper_arm_R','RightForeArm':'lower_arm_R',
         'RightHand':'hand_R','RightShoulder':'shoulder_R','LeftArm':'upper_arm_L',
         'LeftForeArm':'lower_arm_L','LeftHand':'hand_L','Hips':'hips','Spine':'spine_2'}

files = {
    'confused': r'C:\DEV\Avatar-glb\Adam_glb+skelett\confused.glb',
    'idle': r'C:\DEV\EgonsDash\assets\3d\adam\idle_natural.glb',
    'waving': r'C:\DEV\EgonsDash\assets\3d\adam\waving_right.glb',
}

data = {}
for key, path in files.items():
    gltf = GLTF2.load(path)
    names = {i:n.name for i,n in enumerate(gltf.nodes) if n.name}
    d = {}
    for ch in gltf.animations[0].channels:
        if ch.target.path != 'rotation':
            continue
        name = names.get(ch.target.node,'')
        if name not in BONES:
            continue
        s = gltf.animations[0].samplers[ch.sampler]
        qs = read_acc(gltf, s.output)
        d[BONES[name]] = euler(qs[0])
    data[key] = d

print('=== Frame 0 Vergleich: Sind die Skelette gleich? ===')
print(f'{"Bone":<15} {"confused":<28} {"idle":<28} {"waving":<28} {"conf-idle DIFF":<20}')
print('-' * 120)

for bone in ['head','neck','upper_arm_R','lower_arm_R','hand_R','shoulder_R','upper_arm_L','hips']:
    c = data['confused'].get(bone, (0,0,0))
    i = data['idle'].get(bone, (0,0,0))
    w = data['waving'].get(bone, (0,0,0))
    diff = max(abs(c[j]-i[j]) for j in range(3))
    flag = ' *** MISMATCH!' if diff > 10 else ''
    print(f'{bone:<15} ({c[0]:>6.1f},{c[1]:>6.1f},{c[2]:>6.1f})  ({i[0]:>6.1f},{i[1]:>6.1f},{i[2]:>6.1f})  ({w[0]:>6.1f},{w[1]:>6.1f},{w[2]:>6.1f})  diff={diff:>5.1f}{flag}')

# Peak-Analyse
print('\n=== confused.glb: Bewegungsverlauf (welcher Arm bewegt sich?) ===')
gltf = GLTF2.load(files['confused'])
names = {i:n.name for i,n in enumerate(gltf.nodes) if n.name}
for ch in gltf.animations[0].channels:
    if ch.target.path != 'rotation':
        continue
    name = names.get(ch.target.node,'')
    if name not in BONES:
        continue
    s = gltf.animations[0].samplers[ch.sampler]
    qs = read_acc(gltf, s.output)
    motor = BONES[name]
    e0 = euler(qs[0])
    # Max delta from frame 0
    max_delta = 0
    max_frame = 0
    for fi in range(len(qs)):
        e = euler(qs[fi])
        d = max(abs(e[j]-e0[j]) for j in range(3))
        if d > max_delta:
            max_delta = d
            max_frame = fi
    e_peak = euler(qs[max_frame])
    print(f'  {motor:<15} max_delta={max_delta:>6.1f}° at frame {max_frame:>3}  peak=({e_peak[0]:>7.1f},{e_peak[1]:>7.1f},{e_peak[2]:>7.1f})')
