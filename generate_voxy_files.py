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

def extract_shader_parts(filepath):
    """Extracts includes, logic (pre-main), and main body."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Find start of main
    match_main = re.search(r'void\s+main\s*\(\s*\)\s*\{', content)
    if not match_main:
        return "", "", ""

    start_main_index = match_main.end()

    # Find matching closing brace for main
    brace_count = 1
    end_main_index = start_main_index
    while brace_count > 0 and end_main_index < len(content):
        if content[end_main_index] == '{':
            brace_count += 1
        elif content[end_main_index] == '}':
            brace_count -= 1
        end_main_index += 1

    main_body = ""
    if brace_count == 0:
        main_body = content[start_main_index:end_main_index-1]

    # Process pre-main content
    pre_main_raw = content[:match_main.start()]

    includes_block = ""
    logic_block = ""

    for line in pre_main_raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#version"):
            continue
        if "FRAGMENT_SHADER" in line or "GBUFFERS_" in line or "OVERWORLD" in line or "NETHER" in line or "END" in line:
            continue

        if stripped.startswith("#include"):
            includes_block += line + "\n"
        elif stripped.startswith("in ") or stripped.startswith("flat in ") or stripped.startswith("noperspective in ") or stripped.startswith("out "):
            # Skip varying declarations as we mock them locally or provide outputs
            continue
        elif stripped.startswith("uniform "):
            # Skip uniforms (handled by voxy.json and guards)
            continue
        else:
            # Keep logic, comments, other defines
            logic_block += line + "\n"

    return includes_block, logic_block, main_body

# Load all available uniforms
available_uniforms = extract_uniforms('shaders/lib/uniforms.glsl')

# Extract logic
opaque_includes, opaque_logic, opaque_body = extract_shader_parts('shaders/program/gbuffers_terrain.glsl')
translucent_includes, translucent_logic, translucent_body = extract_shader_parts('shaders/program/gbuffers_water.glsl')

# Fix gl_FragData usage
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

        if type_name in ['ivec2', 'ivec3', 'ivec4', 'uvec2', 'uvec3', 'uvec4', 'bvec2', 'bvec3', 'bvec4']:
             continue

        if name == 'inPaleGarden':
            continue

        filtered.append(name)
    return filtered

all_uniforms = sorted(list(available_uniforms.keys()))
final_uniforms = filter_uniforms(all_uniforms, available_uniforms)


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

macros = """
#define texture2D texture
#define texture2DLod textureLod
#define COMPLEMENTARY_VOXY_PATCH

// Mock unsupported uniforms
#ifndef VOXY_MOCK_DEFINED
#define VOXY_MOCK_DEFINED
#endif
"""

polyfill = """
// Polyfill for GetSunVector (Fragment Shader version)
vec3 GetSunVector() {
    const vec2 sunRotationData = vec2(cos(sunPathRotation * 0.01745329251994), -sin(sunPathRotation * 0.01745329251994));
    #ifdef OVERWORLD
        float ang = fract(timeAngle - 0.25);
        ang = (ang + (cos(ang * 3.14159265358979) * -0.5 + 0.5 - ang) / 3.0) * 6.28318530717959;
        return normalize((gbufferModelView * vec4(vec3(-sin(ang), cos(ang) * sunRotationData) * 2000.0, 1.0)).xyz);
    #elif defined END
        float ang = 0.0;
        return normalize((gbufferModelView * vec4(vec3(0.0, sunRotationData * 2000.0), 1.0)).xyz);
    #else
        return vec3(0.0);
    #endif
}
"""

# Opaque GLSL
opaque_glsl = """
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_TERRAIN
#define VOXY

""" + macros + """

""" + opaque_includes + """

""" + polyfill + """

""" + opaque_decls + """

void voxy_emitFragment(VoxyFragmentParameters parameters) {
    vec2 texCoord = parameters.uv;
    vec2 lmCoord = clamp((parameters.lightMap - 0.03125) * 1.06667, 0.0, 1.0);
    vec4 glColor = parameters.tinting;
    int mat = int(parameters.customId);

    vec3 normal = vec3(uint((parameters.face>>1)==2), uint((parameters.face>>1)==0), uint((parameters.face>>1)==1)) * (float(int(parameters.face)&1)*2.0-1.0);

    vec3 voxy_screenPos = vec3(gl_FragCoord.xy / vec2(viewWidth, viewHeight), gl_FragCoord.z);
    vec4 ndc = vec4(voxy_screenPos.xy * 2.0 - 1.0, voxy_screenPos.z * 2.0 - 1.0, 1.0);
    vec4 voxy_viewPos4 = gbufferProjectionInverse * ndc;
    voxy_viewPos4 /= voxy_viewPos4.w;
    vec3 voxy_viewPos = voxy_viewPos4.xyz;
    vec3 vertexPos = (gbufferModelViewInverse * vec4(voxy_viewPos, 1.0)).xyz;

    vec3 upVec = normalize(gbufferModelView[1].xyz);
    vec3 eastVec = normalize(gbufferModelView[0].xyz);
    vec3 northVec = normalize(gbufferModelView[2].xyz);
    vec3 sunVec = GetSunVector();

    ivec2 atlasSize = textureSize(tex, 0);

    vec2 midCoord = vec2(0.0);
    vec2 signMidCoordPos = vec2(0.0);
    vec2 absMidCoordPos = vec2(0.0);
    #if RAIN_PUDDLES >= 1 || defined GENERATED_NORMALS || defined CUSTOM_PBR
        vec3 binormal = vec3(0.0);
        vec3 tangent = vec3(0.0);
    #endif
    #ifdef POM
        vec3 viewVector = voxy_viewPos;
        vec4 vTexCoordAM = vec4(0.0);
    #endif
    #if ANISOTROPIC_FILTER > 0
        vec4 spriteBounds = vec4(0.0);
    #endif

    // Inject Logic (Common Variables)
    """ + opaque_logic + """

    // Body
    """ + opaque_body_fixed + """
}
"""

# Translucent GLSL
translucent_glsl = """
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_WATER
#define VOXY

""" + macros + """

""" + translucent_includes + """

""" + polyfill + """

""" + translucent_decls + """

void voxy_emitFragment(VoxyFragmentParameters parameters) {
    vec2 texCoord = parameters.uv;
    vec2 lmCoord = clamp((parameters.lightMap - 0.03125) * 1.06667, 0.0, 1.0);
    vec4 glColor = parameters.tinting;
    int mat = int(parameters.customId);

    vec3 normal = vec3(uint((parameters.face>>1)==2), uint((parameters.face>>1)==0), uint((parameters.face>>1)==1)) * (float(int(parameters.face)&1)*2.0-1.0);

    vec3 voxy_screenPos = vec3(gl_FragCoord.xy / vec2(viewWidth, viewHeight), gl_FragCoord.z);
    vec4 ndc = vec4(voxy_screenPos.xy * 2.0 - 1.0, voxy_screenPos.z * 2.0 - 1.0, 1.0);
    vec4 voxy_viewPos4 = gbufferProjectionInverse * ndc;
    voxy_viewPos4 /= voxy_viewPos4.w;
    vec3 voxy_viewPos = voxy_viewPos4.xyz;
    vec3 playerPos = (gbufferModelViewInverse * vec4(voxy_viewPos, 1.0)).xyz;

    vec3 upVec = normalize(gbufferModelView[1].xyz);
    vec3 eastVec = normalize(gbufferModelView[0].xyz);
    vec3 northVec = normalize(gbufferModelView[2].xyz);
    vec3 sunVec = GetSunVector();

    ivec2 atlasSize = textureSize(tex, 0);

    vec2 midCoord = vec2(0.0);
    vec2 signMidCoordPos = vec2(0.0);
    vec2 absMidCoordPos = vec2(0.0);
    #if WATER_STYLE >= 2 || RAIN_PUDDLES >= 1 && WATER_STYLE == 1 && WATER_MAT_QUALITY >= 2 || defined GENERATED_NORMALS || defined CUSTOM_PBR
        vec3 binormal = vec3(0.0);
        vec3 tangent = vec3(0.0);
    #endif
    #ifdef POM
        vec3 viewVector = voxy_viewPos;
        vec4 vTexCoordAM = vec4(0.0);
    #endif

    // Inject Logic
    """ + translucent_logic + """

    // Body
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
