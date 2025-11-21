import os
import shutil

def propagate(src_dir, dest_dir, define_old, define_new):
    # Copy json
    shutil.copy(os.path.join(src_dir, 'voxy.json'), os.path.join(dest_dir, 'voxy.json'))

    # Process glsl files
    for filename in ['voxy_opaque.glsl', 'voxy_translucent.glsl']:
        with open(os.path.join(src_dir, filename), 'r') as f:
            content = f.read()

        new_content = content.replace(define_old, define_new)

        with open(os.path.join(dest_dir, filename), 'w') as f:
            f.write(new_content)

propagate('shaders/world0', 'shaders/world-1', '#define OVERWORLD', '#define NETHER')
propagate('shaders/world0', 'shaders/world1', '#define OVERWORLD', '#define END')
