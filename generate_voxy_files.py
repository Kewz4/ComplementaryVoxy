import re
import os
import json

def extract_uniforms(filepath):
    """Extracts all uniforms from the given GLSL file."""
    with open(filepath, 'r') as f:
        content = f.read()
    uniforms = {}
    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] == 'uniform':
            # type is parts[1], name is parts[2] (stripped of ;)
            type_name = parts[1]
            name = parts[2].rstrip(';').split('[')[0]
            uniforms[name] = type_name
    return uniforms

def extract_main_body(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Find start of main
    match = re.search(r'void\s+main\s*\(\s*\)\s*\{', content)
    if not match:
        return None

    start_index = match.end()

    # Find matching closing brace
    brace_count = 1
    end_index = start_index
    while brace_count > 0 and end_index < len(content):
        if content[end_index] == '{':
            brace_count += 1
        elif content[end_index] == '}':
            brace_count -= 1
        end_index += 1

    if brace_count == 0:
        return content[start_index:end_index-1] # Exclude the closing brace
    return None

def get_used_uniforms(source_code, available_uniforms):
    """Returns a list of uniform names that appear in the source code."""
    used = set()
    # Remove comments to avoid false positives
    code_no_comments = re.sub(r'//.*', '', source_code)
    code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)

    for name, type_name in available_uniforms.items():
        if re.search(r'\b' + re.escape(name) + r'\b', code_no_comments):
            used.add(name)

    return sorted(list(used))

# Load all available uniforms
available_uniforms = extract_uniforms('shaders/lib/uniforms.glsl')

# Extract logic
opaque_body = extract_main_body('shaders/program/gbuffers_terrain.glsl')
translucent_body = extract_main_body('shaders/program/gbuffers_water.glsl')

# Fix gl_FragData usage
# Voxy requires us to use explicit output variables mapped to locations 0, 1, 2...
# and map those locations to actual buffers via json.
# The original code assumes gl_FragData[0] goes to the first buffer in DRAWBUFFERS, etc.
# So we replace gl_FragData[x] with voxyOutX and declare them.

def fix_outputs(body):
    # Find max index used
    max_idx = -1
    matches = re.findall(r'gl_FragData\[(\d+)\]', body)
    for m in matches:
        idx = int(m)
        if idx > max_idx:
            max_idx = idx

    # Replace
    for i in range(max_idx + 1):
        body = body.replace(f'gl_FragData[{i}]', f'voxyOut{i}')

    # Generate declarations
    decls = ""
    for i in range(max_idx + 1):
        decls += f"layout(location = {i}) out vec4 voxyOut{i};\n"

    return decls, body

opaque_decls, opaque_body_fixed = fix_outputs(opaque_body)
translucent_decls, translucent_body_fixed = fix_outputs(translucent_body)


def filter_uniforms(uniform_names, available_uniforms_map):
    filtered = []
    for name in uniform_names:
        type_name = available_uniforms_map.get(name)

        # Filter out unsupported types
        if type_name in ['ivec2', 'ivec3', 'ivec4', 'uvec2', 'uvec3', 'uvec4', 'bvec2', 'bvec3', 'bvec4']:
             continue

        # Filter out problematic uniforms
        if name == 'inPaleGarden':
            continue

        filtered.append(name)
    return filtered

all_uniforms = sorted(list(available_uniforms.keys()))
final_uniforms = filter_uniforms(all_uniforms, available_uniforms)


# Samplers list based on common usage in Complementary
samplers = {
    "tex": "sampler2D",
    "noisetex": "sampler2D",
    "colortex0": "sampler2D",
    "colortex1": "sampler2D",
    "colortex2": "sampler2D",
    "colortex3": "sampler2D",
    "colortex4": "sampler2D",
    "colortex5": "sampler2D",
    "colortex6": "sampler2D",
    "colortex7": "sampler2D",
    "colortex8": "sampler2D",
    "depthtex0": "sampler2D",
    "depthtex1": "sampler2D",
    "gaux2": "sampler2D",
    "gaux4": "sampler2D",
    "normals": "sampler2D",
    "specular": "sampler2D",
    "shadowtex0": "sampler2DShadow",
    "shadowtex1": "sampler2DShadow",
    "shadowcolor0": "sampler2D",
    "shadowcolor1": "sampler2D",
    "dhDepthTex": "sampler2D",
    "dhDepthTex1": "sampler2D",
    "floodfill_sampler": "sampler3D",
    "floodfill_sampler_copy": "sampler3D",
    "puddle_sampler": "usampler2D",
    "voxel_sampler": "usampler3D",
    "wsr_sampler": "usampler3D",
    "wsr_sampler_lod": "usampler3D",
    "textureAtlas": "sampler2D"
}

# Opaque GLSL - No #version
opaque_glsl = """
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_TERRAIN
#define COMPLEMENTARY_VOXY_PATCH

#include "/lib/common.glsl"

// Mock unsupported uniforms if necessary
#ifndef VOXY_MOCK_DEFINED
#define VOXY_MOCK_DEFINED
#endif

""" + opaque_decls + """

void voxy_emitFragment(VoxyFragmentParameters parameters) {
    vec2 texCoord = parameters.uv;
    vec2 lmCoord = clamp((parameters.lightMap - 0.03125) * 1.06667, 0.0, 1.0);
    vec4 glColor = parameters.tinting;
    int mat = int(parameters.customId);

    vec3 normal = vec3(uint((parameters.face>>1)==2), uint((parameters.face>>1)==0), uint((parameters.face>>1)==1)) * (float(int(parameters.face)&1)*2.0-1.0);

    vec3 screenPos = vec3(gl_FragCoord.xy / vec2(viewWidth, viewHeight), gl_FragCoord.z);
    vec4 ndc = vec4(screenPos.xy * 2.0 - 1.0, screenPos.z * 2.0 - 1.0, 1.0);
    vec4 viewPos4 = gbufferProjectionInverse * ndc;
    viewPos4 /= viewPos4.w;
    vec3 viewPos = viewPos4.xyz;
    vec3 vertexPos = (gbufferModelViewInverse * vec4(viewPos, 1.0)).xyz;

    vec3 upVec = normalize(gbufferModelView[1].xyz);
    vec3 eastVec = normalize(gbufferModelView[0].xyz);
    vec3 northVec = normalize(gbufferModelView[2].xyz);
    vec3 sunVec = GetSunVector();

    vec2 midCoord = vec2(0.0);
    vec2 signMidCoordPos = vec2(0.0);
    vec2 absMidCoordPos = vec2(0.0);
    #if RAIN_PUDDLES >= 1 || defined GENERATED_NORMALS || defined CUSTOM_PBR
        vec3 binormal = vec3(0.0);
        vec3 tangent = vec3(0.0);
    #endif
    #ifdef POM
        vec3 viewVector = viewPos;
        vec4 vTexCoordAM = vec4(0.0);
    #endif
    #if ANISOTROPIC_FILTER > 0
        vec4 spriteBounds = vec4(0.0);
    #endif

    """ + opaque_body_fixed + """
}
"""

# Translucent GLSL - No #version
translucent_glsl = """
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_WATER
#define COMPLEMENTARY_VOXY_PATCH

#include "/lib/common.glsl"

""" + translucent_decls + """

void voxy_emitFragment(VoxyFragmentParameters parameters) {
    vec2 texCoord = parameters.uv;
    vec2 lmCoord = clamp((parameters.lightMap - 0.03125) * 1.06667, 0.0, 1.0);
    vec4 glColor = parameters.tinting;
    int mat = int(parameters.customId);

    vec3 normal = vec3(uint((parameters.face>>1)==2), uint((parameters.face>>1)==0), uint((parameters.face>>1)==1)) * (float(int(parameters.face)&1)*2.0-1.0);

    vec3 screenPos = vec3(gl_FragCoord.xy / vec2(viewWidth, viewHeight), gl_FragCoord.z);
    vec4 ndc = vec4(screenPos.xy * 2.0 - 1.0, screenPos.z * 2.0 - 1.0, 1.0);
    vec4 viewPos4 = gbufferProjectionInverse * ndc;
    viewPos4 /= viewPos4.w;
    vec3 viewPos = viewPos4.xyz;
    vec3 playerPos = (gbufferModelViewInverse * vec4(viewPos, 1.0)).xyz;

    vec3 upVec = normalize(gbufferModelView[1].xyz);
    vec3 eastVec = normalize(gbufferModelView[0].xyz);
    vec3 northVec = normalize(gbufferModelView[2].xyz);
    vec3 sunVec = GetSunVector();

    vec2 midCoord = vec2(0.0);
    vec2 signMidCoordPos = vec2(0.0);
    vec2 absMidCoordPos = vec2(0.0);
    #if WATER_STYLE >= 2 || RAIN_PUDDLES >= 1 && WATER_STYLE == 1 && WATER_MAT_QUALITY >= 2 || defined GENERATED_NORMALS || defined CUSTOM_PBR
        vec3 binormal = vec3(0.0);
        vec3 tangent = vec3(0.0);
    #endif
    #ifdef POM
        vec3 viewVector = viewPos;
        vec4 vTexCoordAM = vec4(0.0);
    #endif

    """ + translucent_body_fixed + """
}
"""

opaque_db_logic = """
  "opaqueDrawBuffers": [0, 6
    #if BLOCK_REFLECT_QUALITY >= 2 && RP_MODE != 0
    ,4
    #endif
  ],"""
translucent_db_logic = """
  "translucentDrawBuffers": [0, 3
    #if DETAIL_QUALITY >= 3 || (WATER_REFLECT_QUALITY > 0 && WORLD_SPACE_REFLECTIONS > 0)
    ,6
    #if WORLD_SPACE_REFLECTIONS > 0
    ,4,8
    #endif
    #elif WORLD_SPACE_REFLECTIONS > 0
    ,4,8
    #endif
  ],"""

final_json = '{\n  "version": 1,\n  "uniforms": ' + json.dumps(final_uniforms) + ',\n  "samplers": ' + json.dumps(samplers, indent=2) + ',' + opaque_db_logic + translucent_db_logic + '\n  "excludeLodsFromVanillaDepth": true\n}'

with open('shaders/world0/voxy.json', 'w') as f:
    f.write(final_json)
with open('shaders/world0/voxy_opaque.glsl', 'w') as f:
    f.write(opaque_glsl)
with open('shaders/world0/voxy_translucent.glsl', 'w') as f:
    f.write(translucent_glsl)
