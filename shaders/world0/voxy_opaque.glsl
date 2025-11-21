#version 130
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
    gl_FragData[0] = color;
    gl_FragData[1] = vec4(smoothnessD, materialMask, skyLightFactor, 1.0);

    #if BLOCK_REFLECT_QUALITY >= 2 && RP_MODE != 0
        /* DRAWBUFFERS:064 */
        gl_FragData[2] = vec4(mat3(gbufferModelViewInverse) * normalM, 1.0);
    #endif

}
