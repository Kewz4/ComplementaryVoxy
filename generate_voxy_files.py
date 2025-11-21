import re
import os
import json

def extract_uniforms(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    uniforms = set()
    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] == 'uniform':
            name = parts[2].rstrip(';').split('[')[0]
            uniforms.add(name)
    return sorted(list(uniforms))

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

uniforms = extract_uniforms('shaders/lib/uniforms.glsl')
opaque_body = extract_main_body('shaders/program/gbuffers_terrain.glsl')
translucent_body = extract_main_body('shaders/program/gbuffers_water.glsl')

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

final_json = '{\n  "version": 1,\n  "uniforms": ' + json.dumps(uniforms) + ',\n  "samplers": ' + json.dumps(samplers, indent=2) + ',' + opaque_db_logic + translucent_db_logic + '\n  "excludeLodsFromVanillaDepth": true\n}'

with open('shaders/world0/voxy.json', 'w') as f:
    f.write(final_json)
with open('shaders/world0/voxy_opaque.glsl', 'w') as f:
    f.write(opaque_glsl)
with open('shaders/world0/voxy_translucent.glsl', 'w') as f:
    f.write(translucent_glsl)
