"""Inspiziert eine GLB-Datei: Bones, Animationen, Frames, Translation."""
import struct, json, math

def load_glb(path):
    with open(path, 'rb') as f:
        magic, version, length = struct.unpack('<III', f.read(12))
        json_len, json_type = struct.unpack('<II', f.read(8))
        json_data = json.loads(f.read(json_len))
        bin_len, bin_type = struct.unpack('<II', f.read(8))
        bin_data = f.read(bin_len)
    return json_data, bin_data

def read_accessor(gltf, bin_data, idx):
    acc = gltf['accessors'][idx]
    bv = gltf['bufferViews'][acc['bufferView']]
    offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    count = acc['count']
    ctype = acc['componentType']
    dtype = {5126: 'f', 5123: 'H', 5125: 'I'}[ctype]
    size = struct.calcsize(dtype)
    atype = acc['type']
    components = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[atype]
    stride = bv.get('byteStride', size * components)
    result = []
    for i in range(count):
        pos = offset + i * stride
        vals = struct.unpack_from(f'<{components}{dtype}', bin_data, pos)
        result.append(vals if components > 1 else vals[0])
    return result

def quat_to_euler(q):
    x, y, z, w = q
    sinr = 2 * (w * x + y * z)
    cosr = 1 - 2 * (x * x + y * y)
    rx = math.atan2(sinr, cosr)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1, min(1, sinp))
    ry = math.asin(sinp)
    siny = 2 * (w * z + x * y)
    cosy = 1 - 2 * (y * y + z * z)
    rz = math.atan2(siny, cosy)
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))

path = r'C:\DEV\Avatar-glb\Winken\Meshy_AI_Animation_Wave_for_Help_2_withSkin.glb'
print(f"=== Inspecting: {path} ===\n")

gltf, bin_data = load_glb(path)

# Nodes
nodes = gltf.get('nodes', [])
print(f"Nodes ({len(nodes)}):")
for i, n in enumerate(nodes):
    name = n.get('name', '(unnamed)')
    rot = n.get('rotation')
    trans = n.get('translation')
    print(f"  [{i}] {name}", end="")
    if rot:
        euler = quat_to_euler(rot)
        print(f"  rot=({euler[0]:.1f}, {euler[1]:.1f}, {euler[2]:.1f})", end="")
    if trans:
        print(f"  trans=({trans[0]:.3f}, {trans[1]:.3f}, {trans[2]:.3f})", end="")
    print()

# Animations
anims = gltf.get('animations', [])
print(f"\nAnimations ({len(anims)}):")
for ai, anim in enumerate(anims):
    print(f"  [{ai}] {anim.get('name', '(unnamed)')}")
    channels = anim['channels']
    samplers = anim['samplers']
    print(f"    Channels: {len(channels)}, Samplers: {len(samplers)}")

    for ci, ch in enumerate(channels):
        node_idx = ch['target'].get('node', -1)
        path_type = ch['target']['path']
        bone_name = nodes[node_idx].get('name', '?') if 0 <= node_idx < len(nodes) else '?'
        sampler = samplers[ch['sampler']]
        times = read_accessor(gltf, bin_data, sampler['input'])
        values = read_accessor(gltf, bin_data, sampler['output'])

        print(f"    Ch[{ci}] {bone_name}.{path_type}: {len(times)} frames, {times[0]:.3f}s - {times[-1]:.3f}s")

        if path_type == 'rotation' and len(values) > 0:
            euler_0 = quat_to_euler(values[0])
            euler_last = quat_to_euler(values[-1])
            # Find max delta from frame 0
            max_delta = [0, 0, 0]
            for v in values:
                e = quat_to_euler(v)
                for ax in range(3):
                    d = abs(e[ax] - euler_0[ax])
                    if d > max_delta[ax]:
                        max_delta[ax] = d
            print(f"      Frame0 euler: ({euler_0[0]:.1f}, {euler_0[1]:.1f}, {euler_0[2]:.1f})")
            print(f"      Max delta from F0: rx={max_delta[0]:.1f} ry={max_delta[1]:.1f} rz={max_delta[2]:.1f}")

        if path_type == 'translation' and len(values) > 0:
            v0 = values[0]
            max_delta = [0, 0, 0]
            for v in values:
                for ax in range(3):
                    d = abs(v[ax] - v0[ax])
                    if d > max_delta[ax]:
                        max_delta[ax] = d
            print(f"      Frame0 trans: ({v0[0]:.4f}, {v0[1]:.4f}, {v0[2]:.4f})")
            print(f"      Max delta from F0: tx={max_delta[0]:.4f} ty={max_delta[1]:.4f} tz={max_delta[2]:.4f}")
