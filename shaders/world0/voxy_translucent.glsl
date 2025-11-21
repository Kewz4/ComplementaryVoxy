
#define FRAGMENT_SHADER
#define OVERWORLD
#define GBUFFERS_WATER
#define VOXY

#include "/lib/common.glsl"

layout(location = 0) out vec4 voxyOut0;
layout(location = 1) out vec4 voxyOut1;
layout(location = 2) out vec4 voxyOut2;
layout(location = 3) out vec4 voxyOut3;
layout(location = 4) out vec4 voxyOut4;


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


    vec4 colorP = texture2D(tex, texCoord);
    vec4 color = colorP * vec4(glColor.rgb, 1.0);

    vec3 screenPos = vec3(gl_FragCoord.xy / vec2(viewWidth, viewHeight), gl_FragCoord.z);
    #ifdef TAA
        vec3 viewPos = ScreenToView(vec3(TAAJitter(screenPos.xy, -0.5), screenPos.z));
    #else
        vec3 viewPos = ScreenToView(screenPos);
    #endif
    float lViewPos = length(viewPos);

    float dither = Bayer64(gl_FragCoord.xy);
    #ifdef TAA
        dither = fract(dither + goldenRatio * mod(float(frameCounter), 3600.0));
    #endif

    #ifdef LIGHT_COLOR_MULTS
        lightColorMult = GetLightColorMult();
    #endif
    #ifdef ATM_COLOR_MULTS
        atmColorMult = GetAtmColorMult();
        sqrtAtmColorMult = sqrt(atmColorMult);
    #endif

    #ifdef VL_CLOUDS_ACTIVE
        float cloudLinearDepth = texelFetch(gaux2, texelCoord, 0).a;

        if (pow2(cloudLinearDepth + OSIEBCA * dither) * renderDistance < min(lViewPos, renderDistance)) discard;
    #endif

    float materialMask = 0.0;

    vec3 nViewPos = normalize(viewPos);
    float VdotU = dot(nViewPos, upVec);
    float VdotS = dot(nViewPos, sunVec);
    float VdotN = dot(nViewPos, normal);

    // Materials
    vec4 translucentMult = vec4(1.0);
    bool noSmoothLighting = false, noDirectionalShading = false, translucentMultCalculated = false, noGeneratedNormals = false;
    int subsurfaceMode = 0;
    vec2 lmCoordM = lmCoord;
    float smoothnessG = 0.0, highlightMult = 1.0, reflectMult = 0.0, emission = 0.0;
    vec3 normalM = VdotN > 0.0 ? -normal : normal; // Inverted Iris Water Normal Workaround
    vec3 geoNormal = normalM;
    vec3 worldGeoNormal = normalize(ViewToPlayer(geoNormal * 10000.0));
    vec3 shadowMult = vec3(1.0);
    float fresnel = clamp(1.0 + dot(normalM, nViewPos), 0.0, 1.0);
    float fresnelM = pow3(fresnel);
    #ifdef IPBR
        #include "/lib/materials/materialHandling/translucentIPBR.glsl"

        #ifdef GENERATED_NORMALS
            if (!noGeneratedNormals) GenerateNormals(normalM, colorP.rgb * colorP.a * 1.5);
        #endif

        #if IPBR_EMISSIVE_MODE != 1
            emission = GetCustomEmissionForIPBR(color, emission);
        #endif
    #else
        #ifdef CUSTOM_PBR
            float smoothnessD, materialMaskPh;
            GetCustomMaterials(color, normalM, lmCoordM, NdotU, shadowMult, smoothnessG, smoothnessD, highlightMult, emission, materialMaskPh, viewPos, lViewPos);
            reflectMult = smoothnessD;
        #endif

        if (mat == 32000) { // Water
            #include "/lib/materials/specificMaterials/translucents/water.glsl"
        } else if (mat == 30020) { // Nether Portal
            #ifdef SPECIAL_PORTAL_EFFECTS
                #include "/lib/materials/specificMaterials/translucents/netherPortal.glsl"
            #endif
        }
    #endif

    #if WATER_MAT_QUALITY >= 3 && SELECT_OUTLINE == 4
        int materialMaskInt = int(texelFetch(colortex6, texelCoord, 0).g * 255.1);
        if (materialMaskInt == 252) {
            materialMask = OSIEBCA * 252.0; // Versatile Selection Outline
        }
    #endif

    // Blending
    if (!translucentMultCalculated)
        translucentMult = vec4(mix(vec3(0.666), color.rgb * (1.0 - pow2(pow2(color.a))), color.a), 1.0);

    translucentMult.rgb = mix(translucentMult.rgb, vec3(1.0), min1(pow2(pow2(lViewPos / far))));

    // Lighting
    DoLighting(color, shadowMult, playerPos, viewPos, lViewPos, geoNormal, normalM, dither,
               worldGeoNormal, lmCoordM, noSmoothLighting, noDirectionalShading, false,
               false, subsurfaceMode, smoothnessG, highlightMult, emission);

    // Reflections
    float skyLightFactor = GetSkyLightFactor(lmCoordM, shadowMult);
    #if WATER_REFLECT_QUALITY >= 0
        #ifdef LIGHT_COLOR_MULTS
            highlightColor *= lightColorMult;
        #endif
        #ifdef MOON_PHASE_INF_REFLECTION
            highlightColor *= pow2(moonPhaseInfluence);
        #endif

        fresnelM = (fresnelM * 0.85 + 0.15) * reflectMult;

        vec4 reflection = GetReflection(normalM, viewPos.xyz, nViewPos, playerPos, lViewPos, -1.0,
                                        depthtex1, dither, skyLightFactor, fresnel,
                                        smoothnessG, geoNormal, color.rgb, shadowMult, highlightMult);
        color.rgb = mix(color.rgb, reflection.rgb, fresnelM);

    #else
        fresnelM = 0.0;
        vec4 reflection = vec4(0.0);
    #endif
    ////

    #ifdef COLOR_CODED_PROGRAMS
        ColorCodeProgram(color, mat);
    #endif

    float skyFade = 0.0;
    float prevAlpha = color.a;
    color.a = 1.0;
    DoFog(color, skyFade, lViewPos, playerPos, VdotU, VdotS, dither);
    float fogAlpha = color.a;
    color.a = prevAlpha * (1.0 - skyFade);

    /* DRAWBUFFERS:03 */
    voxyOut0 = color;
    voxyOut1 = vec4(1.0 - translucentMult.rgb, translucentMult.a);

    #if DETAIL_QUALITY >= 3 || (WATER_REFLECT_QUALITY > 0 && WORLD_SPACE_REFLECTIONS > 0)
        /* DRAWBUFFERS:036 */
        voxyOut2 = vec4(1.0, materialMask, skyLightFactor, 1.0);

        #if WORLD_SPACE_REFLECTIONS > 0
            /* DRAWBUFFERS:03648 */
            voxyOut3 = vec4(mat3(gbufferModelViewInverse) * normalM, sqrt(fresnelM * color.a * fogAlpha));
            voxyOut4 = vec4(reflection.rgb * fresnelM * color.a * fogAlpha, reflection.a);
        #endif
    #elif WORLD_SPACE_REFLECTIONS > 0
        /* DRAWBUFFERS:0348 */
        voxyOut2 = vec4(mat3(gbufferModelViewInverse) * normalM, sqrt(fresnelM * color.a * fogAlpha));
        voxyOut3 = vec4(reflection.rgb * fresnelM * color.a * fogAlpha, reflection.a);
    #endif

}
