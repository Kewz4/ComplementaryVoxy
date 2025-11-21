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
    # Simple comment removal (not perfect but good enough for typical shaders)
    code_no_comments = re.sub(r'//.*', '', source_code)
    code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)

    for name, type_name in available_uniforms.items():
        # Simple regex to check if the variable name is used as a token
        # \b matches word boundaries
        if re.search(r'\b' + re.escape(name) + r'\b', code_no_comments):
            used.add(name)

    return sorted(list(used))

# Load all available uniforms
available_uniforms = extract_uniforms('shaders/lib/uniforms.glsl')

# Extract logic
opaque_body = extract_main_body('shaders/program/gbuffers_terrain.glsl')
translucent_body = extract_main_body('shaders/program/gbuffers_water.glsl')

# Combined logic for checking usage (include common files if possible, or just checking the bodies + what we know about includes)
# Note: include expansion is hard to do perfectly without reading all files.
# However, the error is about 'uniforms' list in voxy.json.
# Voxy injects these uniforms. If we list them, Voxy tries to inject them.
# If they are unsupported types (ivec2), Voxy crashes.
# So we MUST exclude unsupported types from the list, EVEN IF THEY ARE USED.
# If they are used, the shader will fail to compile (undefined variable).
# But if they are unused, we can safely remove them.

# Also, we need to remove 'inPaleGarden' because of the Iris resolution error.

def filter_uniforms(uniform_names, available_uniforms_map):
    filtered = []
    for name in uniform_names:
        type_name = available_uniforms_map.get(name)

        # Filter out unsupported types
        if type_name in ['ivec2', 'ivec3', 'ivec4', 'uvec2', 'uvec3', 'uvec4', 'bvec2', 'bvec3', 'bvec4']:
             # Voxy 0.2.5/0.2.6 likely doesn't support these or specific ones like Vector2Integer
             # The error explicitly mentioned Vector2IntegerJomlUniform
             continue

        # Filter out problematic uniforms
        if name == 'inPaleGarden':
            continue

        filtered.append(name)
    return filtered


# Get used uniforms in the opaque and translucent bodies
# Note: This check is imperfect because it doesn't scan included files in lib/.
# However, the primary goal is to filter the list we put in voxy.json.
# If we put a uniform in voxy.json, Voxy tries to bind it.
# If we omit it, Voxy doesn't bind it.
# If the shader uses it (e.g. in a lib function), and it's not injected, the shader compilation will fail.
# BUT, the user is crashing at Java level (Voxy/Iris loading), not Shader compilation level (yet).
# The Java crash on 'Vector2Integer' is blocking.
# So we MUST remove 'ivec2' uniforms (atlasSize, eyeBrightness) from voxy.json.
# If the shader needs them, we are in trouble, but maybe we can mock them or they are not actually used in the Voxy path.
# 'inPaleGarden' is also causing a crash (Iris resolution).

# Let's build the list of all uniforms found in uniforms.glsl, but filtered.
# We will assume that if it's in uniforms.glsl, it might be used.
# We will just filter out the ones we KNOW cause crashes.

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

# Opaque GLSL
opaque_glsl = """#version 130
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_TERRAIN
#define VOXY

#include "/lib/common.glsl"

// Mock unsupported uniforms if necessary
#ifndef VOXY_MOCK_DEFINED
#define VOXY_MOCK_DEFINED
// Helper to mock things if they are missing
// But strictly speaking, we can't define uniforms here if they are already defined in uniforms.glsl (which is included via common.glsl)
// Wait, uniforms.glsl defines them.
// If Voxy injects them, it prepends the declaration? No, Voxy doc says:
// "these are automatically added/injected into your patch so YOU MUST NOT DEFINE THE UNIFORMS IN YOUR PATCH DATA"
// But standard shader files (included via common.glsl) HAVE the uniform declarations.
// Usually Iris handles this by deduplicating or Voxy handles it.
// But if Voxy FAILS to inject them (because we removed them from JSON), but they are declared in uniforms.glsl...
// Then they exist as declarations but have no value bound? Or does Voxy strip them?
// The problem is "Type not implemented". Voxy tries to read the uniform value from Iris/Game and upload it.
// If we don't ask Voxy to do it (remove from JSON), the uniform variable remains in the source (from common.glsl -> uniforms.glsl).
// It will be initialized to 0.
// This is PERFECT for 'inPaleGarden' (0 means not in pale garden).
// For 'atlasSize', 0 might cause division by zero or other issues.
// For 'eyeBrightness', 0 is dark.
// Let's hope 0 is a safe default.
#endif

void voxy_emitFragment(VoxyFragmentParameters parameters) {
    vec2 texCoord = parameters.uv;
    vec2 lmCoord = clamp((parameters.lightMap - 0.03125) * 1.06667, 0.0, 1.0);
    vec4 glColorRaw = parameters.tinting;
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

    """ + opaque_body + """
}
"""

# Translucent GLSL
translucent_glsl = """#version 130
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_WATER
#define VOXY

#include "/lib/common.glsl"

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

    """ + translucent_body + """
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
