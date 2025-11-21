
#define FRAGMENT_SHADER
#define NETHER
#define GBUFFERS_TERRAIN
#define VOXY


#define texture2D texture
#define texture2DLod textureLod
#define COMPLEMENTARY_VOXY_PATCH

// Mock unsupported uniforms
#ifndef VOXY_MOCK_DEFINED
#define VOXY_MOCK_DEFINED
#endif


#include "/lib/common.glsl"
#include "/lib/util/spaceConversion.glsl"
#include "/lib/lighting/mainLighting.glsl"
#include "/lib/util/dither.glsl"
    #include "/lib/antialiasing/jitter.glsl"
    #include "/lib/util/miplevel.glsl"
    #include "/lib/materials/materialMethods/generatedNormals.glsl"
    #include "/lib/materials/materialMethods/coatedTextures.glsl"
    #include "/lib/materials/materialMethods/customEmission.glsl"
    #include "/lib/materials/materialHandling/customMaterials.glsl"
    #include "/lib/misc/colorCodedPrograms.glsl"
    #include "/lib/materials/materialMethods/anisotropicFiltering.glsl"
    #include "/lib/voxelization/puddleVoxelization.glsl"
    #include "/lib/materials/materialMethods/snowyWorld.glsl"
    #include "/lib/misc/distantLightBokeh.glsl"



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


layout(location = 0) out vec4 voxyOut0;
layout(location = 1) out vec4 voxyOut1;
layout(location = 2) out vec4 voxyOut2;


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
    /////////////////////////////////////
// Complementary Shaders by EminGT //
/////////////////////////////////////

//Common//

//////////Fragment Shader//////////Fragment Shader//////////Fragment Shader//////////





#if RAIN_PUDDLES >= 1 || defined GENERATED_NORMALS || defined CUSTOM_PBR
#endif

#ifdef POM

#endif

#if ANISOTROPIC_FILTER > 0
#endif

//Pipeline Constants//
#if COLORED_LIGHTING_INTERNAL > 0
    #if WORLD_SPACE_REFLECTIONS_INTERNAL == -1
        const float voxelDistance = 32.0;
    #else
        const float voxelDistance = 64.0;
    #endif
#endif

//Common Variables//
float NdotU = dot(normal, upVec);
float geoNdotU = NdotU;
float NdotUmax0 = max(NdotU, 0.0);
float SdotU = dot(sunVec, upVec);
float sunFactor = SdotU < 0.0 ? clamp(SdotU + 0.375, 0.0, 0.75) / 0.75 : clamp(SdotU + 0.03125, 0.0, 0.0625) / 0.0625;
float sunVisibility = clamp(SdotU + 0.0625, 0.0, 0.125) / 0.125;
float sunVisibility2 = sunVisibility * sunVisibility;
float shadowTimeVar1 = abs(sunVisibility - 0.5) * 2.0;
float shadowTimeVar2 = shadowTimeVar1 * shadowTimeVar1;
float shadowTime = shadowTimeVar2 * shadowTimeVar2;

vec4 glColor = glColorRaw;

    vec3 lightVec = sunVec * ((timeAngle < 0.5325 || timeAngle > 0.9675) ? 1.0 : -1.0);
#else
    vec3 lightVec = sunVec;
#endif

#if RAIN_PUDDLES >= 1 || defined GENERATED_NORMALS || defined CUSTOM_PBR
    mat3 tbnMatrix = mat3(
        tangent.x, binormal.x, normal.x,
        tangent.y, binormal.y, normal.y,
        tangent.z, binormal.z, normal.z
    );
#endif

//Common Functions//
void DoFoliageColorTweaks(inout vec3 color, inout vec3 shadowMult, inout float snowMinNdotU, vec3 viewPos, vec3 nViewPos, float lViewPos, float dither) {
    float factor = max(80.0 - lViewPos, 0.0);
    shadowMult *= 1.0 + 0.004 * noonFactor * factor;

    #if defined IPBR && !defined IPBR_COMPAT_MODE
        color.rgb *= 0.97 - 0.2 * signMidCoordPos.x;
    #endif

    //#define FOLIAGE_ALT_SUBSURFACE

    #ifdef FOLIAGE_ALT_SUBSURFACE
        float edgeSize = 0.12;
        float edgeEffectFactor = 0.75;

        vec2 texCoordM = texCoord;
             texCoordM.y -= edgeSize * dither * absMidCoordPos.y;
             texCoordM.y = max(texCoordM.y, midCoord.y - absMidCoordPos.y);
        vec4 colorSample = texture2DLod(tex, texCoordM, 0);

        if (colorSample.a < 0.5) {
            float edgeFactor = dot(nViewPos, lightVec);
            shadowMult *= 1.0 + edgeEffectFactor * (1.0 + edgeFactor);
        }

        shadowMult *= 1.03 + 0.2333 * edgeEffectFactor * (dot(normal, lightVec) - 1.0);
    #endif

    #ifdef SNOWY_WORLD
        if (glColor.g - glColor.b > 0.01)
            snowMinNdotU = min(pow2(pow2(max0(color.g * 2.0 - color.r - color.b))) * 5.0, 0.1);
        else
            snowMinNdotU = min(pow2(pow2(max0(color.g * 2.0 - color.r - color.b))) * 3.0, 0.1) * 0.25;

        #ifdef DISTANT_HORIZONS
            // DH chunks don't have foliage. The border looks too noticeable without this tweak
            snowMinNdotU = mix(snowMinNdotU, 0.09, smoothstep(far * 0.5, far, lViewPos));
        #endif
    #endif
}

void DoBrightBlockTweaks(vec3 color, float minLight, inout vec3 shadowMult, inout float highlightMult) {
    float factor = mix(minLight * 0.5 + 0.5, 1.0, pow2(pow2(color.r)));
    shadowMult = vec3(factor);
    highlightMult /= factor;
}

void DoOceanBlockTweaks(inout float smoothnessD) {
    smoothnessD *= max0(lmCoord.y - 0.95) * 20.0;
}

//Includes//

#ifdef TAA
#endif

#if defined GENERATED_NORMALS || defined COATED_TEXTURES || ANISOTROPIC_FILTER > 0 || defined DISTANT_LIGHT_BOKEH
#endif

#ifdef GENERATED_NORMALS
#endif

#ifdef COATED_TEXTURES
#endif

#if IPBR_EMISSIVE_MODE != 1
#endif

#ifdef CUSTOM_PBR
#endif

#ifdef COLOR_CODED_PROGRAMS
#endif

#if ANISOTROPIC_FILTER > 0
#endif

#ifdef PUDDLE_VOXELIZATION
#endif

#ifdef SNOWY_WORLD
#endif

#ifdef DISTANT_LIGHT_BOKEH
#endif

//Program//


    // Body

    #if ANISOTROPIC_FILTER == 0
        vec4 color = texture2D(tex, texCoord);
    #else
        vec4 color = textureAF(tex, texCoord);
    #endif

    float smoothnessD = 0.0, materialMask = 0.0;

    #if !defined POM || !defined POM_ALLOW_CUTOUT
        if (color.a <= 0.00001) discard; // 6WIR4HT23
    #endif

    vec3 colorP = color.rgb;
    color.rgb *= glColor.rgb;

    vec3 screenPos = vec3(gl_FragCoord.xy / vec2(viewWidth, viewHeight), gl_FragCoord.z);
    #ifdef TAA
        vec3 viewPos = ScreenToView(vec3(TAAJitter(screenPos.xy, -0.5), screenPos.z));
    #else
        vec3 viewPos = ScreenToView(screenPos);
    #endif
    float lViewPos = length(viewPos);
    vec3 nViewPos = normalize(viewPos);
    vec3 playerPos = vertexPos;

    float dither = Bayer64(gl_FragCoord.xy);
    #ifdef TAA
        dither = fract(dither + goldenRatio * mod(float(frameCounter), 3600.0));
    #endif

    int subsurfaceMode = 0;
    bool noSmoothLighting = false, noDirectionalShading = false, noVanillaAO = false, centerShadowBias = false, noGeneratedNormals = false, doTileRandomisation = true;
    float smoothnessG = 0.0, highlightMult = 1.0, emission = 0.0, noiseFactor = 1.0, snowFactor = 1.0, snowMinNdotU = 0.0, noPuddles = 0.0;
    vec2 lmCoordM = lmCoord;
    vec3 normalM = normal, geoNormal = normal, shadowMult = vec3(1.0);
    vec3 worldGeoNormal = normalize(ViewToPlayer(geoNormal * 10000.0));

    #ifdef IPBR
        vec3 maRecolor = vec3(0.0);
        #include "/lib/materials/materialHandling/terrainIPBR.glsl"

        #ifdef GENERATED_NORMALS
            if (!noGeneratedNormals) GenerateNormals(normalM, colorP);
        #endif

        #ifdef COATED_TEXTURES
            CoatTextures(color.rgb, noiseFactor, playerPos, doTileRandomisation);
        #endif

        #if IPBR_EMISSIVE_MODE != 1
            emission = GetCustomEmissionForIPBR(color, emission);
        #endif
    #else
        #ifdef CUSTOM_PBR
            GetCustomMaterials(color, normalM, lmCoordM, NdotU, shadowMult, smoothnessG, smoothnessD, highlightMult, emission, materialMask, viewPos, lViewPos);
        #endif

        if (mat == 10001) { // No directional shading
            noDirectionalShading = true;
        } else if (mat == 10005) { // Grounded Waving Foliage
            subsurfaceMode = 1, noSmoothLighting = true, noDirectionalShading = true;
            DoFoliageColorTweaks(color.rgb, shadowMult, snowMinNdotU, viewPos, nViewPos, lViewPos, dither);
        } else if (mat == 10009) { // Leaves
            #include "/lib/materials/specificMaterials/terrain/leaves.glsl"
        } else if (mat == 10013) { // Vine
            subsurfaceMode = 3, centerShadowBias = true; noSmoothLighting = true;
        } else if (mat == 10017) { // Non-waving Foliage
            subsurfaceMode = 1, noSmoothLighting = true, noDirectionalShading = true;
        } else if (mat == 10021) { // Upper Waving Foliage
            subsurfaceMode = 1, noSmoothLighting = true, noDirectionalShading = true;
            DoFoliageColorTweaks(color.rgb, shadowMult, snowMinNdotU, viewPos, nViewPos, lViewPos, dither);
        } else if (mat == 10028) { // Modded Light Sources
            noSmoothLighting = true; noDirectionalShading = true;
            emission = GetLuminance(color.rgb) * 2.5;
        }

        #ifdef SNOWY_WORLD
        else if (mat == 10132) { // Grass Block:Normal
            if (glColor.b < 0.999) { // Grass Block:Normal:Grass Part
                snowMinNdotU = min(pow2(pow2(color.g)) * 1.9, 0.1);
                color.rgb = color.rgb * 0.5 + 0.5 * (color.rgb / glColor.rgb);
            }
        }
        #endif

        else if (lmCoord.x > 0.99999) lmCoordM.x = 0.95;
    #endif

    #ifdef SNOWY_WORLD
        DoSnowyWorld(color, smoothnessG, highlightMult, smoothnessD, emission,
                     playerPos, lmCoord, snowFactor, snowMinNdotU, NdotU, subsurfaceMode);
    #endif

    #if RAIN_PUDDLES >= 1
        float puddleLightFactor = max0(lmCoord.y * 32.0 - 31.0) * clamp((1.0 - 1.15 * lmCoord.x) * 10.0, 0.0, 1.0);
        float puddleNormalFactor = pow2(max0(NdotUmax0 - 0.5) * 2.0);
        float puddleMixer = puddleLightFactor * inRainy * puddleNormalFactor;
        #if RAIN_PUDDLES < 3
            float wetnessM = wetness;
        #else
            float wetnessM = 1.0;
        #endif
        #ifdef PUDDLE_VOXELIZATION
            vec3 voxelPos = SceneToPuddleVoxel(playerPos);
            vec3 voxel_sample_pos = clamp01(voxelPos / vec3(puddle_voxelVolumeSize));
            if (CheckInsidePuddleVoxelVolume(voxelPos)) {
                noPuddles += texture2D(puddle_sampler, voxel_sample_pos.xz).r;
            }
        #endif
        if (pow2(pow2(wetnessM)) * puddleMixer - noPuddles > 0.00001) {
            vec2 worldPosXZ = playerPos.xz + cameraPosition.xz;
            vec2 puddleWind = vec2(frameTimeCounter) * 0.03;
            #if WATER_STYLE == 1
                vec2 puddlePosNormal = floor(worldPosXZ * 16.0) * 0.0625;
            #else
                vec2 puddlePosNormal = worldPosXZ;
            #endif

            puddlePosNormal *= 0.1;
            vec2 pNormalCoord1 = puddlePosNormal + vec2(puddleWind.x, puddleWind.y);
            vec2 pNormalCoord2 = puddlePosNormal + vec2(puddleWind.x * -1.5, puddleWind.y * -1.0);
            vec3 pNormalNoise1 = texture2DLod(noisetex, pNormalCoord1, 0.0).rgb;
            vec3 pNormalNoise2 = texture2DLod(noisetex, pNormalCoord2, 0.0).rgb;
            float pNormalMult = 0.03;

            vec3 puddleNormal = vec3((pNormalNoise1.xy + pNormalNoise2.xy - vec2(1.0)) * pNormalMult, 1.0);
            puddleNormal = clamp(normalize(puddleNormal * tbnMatrix), vec3(-1.0), vec3(1.0));

            #if RAIN_PUDDLES == 1 || RAIN_PUDDLES == 3
                vec2 puddlePosForm = puddlePosNormal * 0.05;
                float pFormNoise  = texture2DLod(noisetex, puddlePosForm, 0.0).b        * 3.0;
                      pFormNoise += texture2DLod(noisetex, puddlePosForm * 0.5, 0.0).b  * 5.0;
                      pFormNoise += texture2DLod(noisetex, puddlePosForm * 0.25, 0.0).b * 8.0;
                      pFormNoise *= sqrt1(wetnessM) * 0.5625 + 0.4375;
                      pFormNoise  = clamp(pFormNoise - 7.0, 0.0, 1.0);
            #else
                float pFormNoise = wetnessM;
            #endif
            puddleMixer *= pFormNoise;

            float puddleSmoothnessG = 0.7 - rainFactor * 0.3;
            float puddleHighlight = (1.5 - subsurfaceMode * 0.6 * invNoonFactor);
            smoothnessG = mix(smoothnessG, puddleSmoothnessG, puddleMixer);
            highlightMult = mix(highlightMult, puddleHighlight, puddleMixer);
            smoothnessD = mix(smoothnessD, 1.0, sqrt1(puddleMixer));
            normalM = mix(normalM, puddleNormal, puddleMixer * rainFactor);
        }
    #endif

    #if SHOW_LIGHT_LEVEL > 0
        #include "/lib/misc/showLightLevels.glsl"
    #endif

    DoLighting(color, shadowMult, playerPos, viewPos, lViewPos, geoNormal, normalM, dither,
               worldGeoNormal, lmCoordM, noSmoothLighting, noDirectionalShading, noVanillaAO,
               centerShadowBias, subsurfaceMode, smoothnessG, highlightMult, emission);

    #ifdef IPBR
        color.rgb += maRecolor;
    #endif

    float skyLightFactor = GetSkyLightFactor(lmCoordM, shadowMult);

    #ifdef COLOR_CODED_PROGRAMS
        ColorCodeProgram(color, mat);
    #endif

    /* DRAWBUFFERS:06 */
    voxyOut0 = color;
    voxyOut1 = vec4(smoothnessD, materialMask, skyLightFactor, 1.0);

    #if BLOCK_REFLECT_QUALITY >= 2 && RP_MODE != 0
        /* DRAWBUFFERS:064 */
        voxyOut2 = vec4(mat3(gbufferModelViewInverse) * normalM, 1.0);
    #endif

}
