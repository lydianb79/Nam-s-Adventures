// Soft "toy" shading for every model and the terrain: wrapped diffuse with a gentle ramp, cool sky-tinted
// shadows, glossy highlight, fresnel rim light, emission, optional wind sway for vegetation.
Shader "Nam/Toon"
{
    Properties
    {
        _BaseMap ("Texture", 2D) = "white" {}
        _BaseColor ("Color", Color) = (1,1,1,1)
        _Smoothness ("Smoothness", Range(0,1)) = 0.3
        [HDR] _EmissionColor ("Emission", Color) = (0,0,0,0)
        _Rim ("Rim strength", Range(0,2)) = 0.55
        _Wind ("Wind sway", Range(0,2)) = 0
        _WindUV ("Wind by UV height (grass blades)", Range(0,1)) = 0
        _Detail ("Surface detail (grey, triplanar)", 2D) = "gray" {}
        _DetailN ("Surface detail normal map", 2D) = "bump" {}
        _DetailScale ("Detail tiles per unit", Float) = 2
        _DetailAmt ("Detail strength", Range(0,1)) = 0
        _DetailBump ("Detail relief", Range(0,1)) = 0.5
        _Cull ("Cull (2 back, 0 off)", Float) = 2
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        TEXTURE2D(_Detail); SAMPLER(sampler_Detail);
        TEXTURE2D(_DetailN); SAMPLER(sampler_DetailN);
        CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST;
        half4 _BaseColor;
        half _Smoothness;
        half4 _EmissionColor;
        half _Rim;
        half _Wind;
        half _WindUV;
        half _Cull;
        half _DetailScale;
        half _DetailAmt;
        half _DetailBump;
        CBUFFER_END
        half4 _NamSky;      // ambient from above
        half4 _NamGround;   // ambient from below
        float4 _NamPlayer;  // xyz = Nam's position (grass bends away from her), w = her speed

        // Props sway with height above their origin. Grass blades (one big mesh) use uv.y as the height
        // along the blade instead, ripple with gusts that travel across the field, and part around Nam.
        float3 WindWS(float3 positionOS, float2 uv)
        {
            float3 ws = TransformObjectToWorld(positionOS);
            float t = _Time.y;
            if (_WindUV > 0.5)
            {
                float k = uv.y * uv.y;
                float gust = sin(ws.x * 0.42 - t * 1.5 + ws.z * 0.3) * 0.5 + 0.5;
                ws.x += (sin(t * 2.3 + ws.x * 1.9 + ws.z * 2.7) * 0.035 + gust * 0.075) * k * _Wind;
                ws.z += cos(t * 1.9 + ws.x * 2.3) * 0.03 * k * _Wind;
                float2 d = ws.xz - _NamPlayer.xz;
                float near = saturate(1.0 - length(d) / 0.75) * saturate(1.0 - abs(ws.y - _NamPlayer.y - 0.2) / 0.9);
                ws.xz += normalize(d + 0.0001) * near * 0.3 * uv.y;
                ws.y -= near * 0.12 * uv.y;
                return ws;
            }
            float3 origin = TransformObjectToWorld(float3(0, 0, 0));
            float h = max(0, ws.y - origin.y);
            float ph = origin.x * 0.7 + origin.z * 1.3;
            float a = _Wind * 0.022 * pow(h, 1.4);
            ws.x += (sin(t * 1.7 + ph) + 0.4 * sin(t * 3.9 + ph * 2.0 + ws.y)) * a;
            ws.z += cos(t * 1.3 + ph) * a * 0.6;
            return ws;
        }
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile_fog

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                float3 normalWS : TEXCOORD2;
                float fog : TEXCOORD3;
                float3 detailPos : TEXCOORD4;     // object-space position in world units: the detail sticks to the object
                float3 normalOS : TEXCOORD5;
            };

            Varyings vert (Attributes v)
            {
                Varyings o;
                o.positionWS = WindWS(v.positionOS.xyz, v.uv);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.fog = ComputeFogFactor(o.positionCS.z);
                float3 sc = float3(length(UNITY_MATRIX_M._m00_m10_m20), length(UNITY_MATRIX_M._m01_m11_m21), length(UNITY_MATRIX_M._m02_m12_m22));
                o.detailPos = v.positionOS.xyz * sc;
                o.normalOS = v.normalOS;
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb * _BaseColor.rgb;
                half3 N = normalize(i.normalWS);
                half3 V = normalize(GetWorldSpaceViewDir(i.positionWS));
                // surface detail: a grey map projected from three sides, tinting the colour and bumping the normal
                if (_DetailAmt > 0.001)
                {
                    float3 p = i.detailPos * _DetailScale;
                    float3 bw = pow(abs(normalize(i.normalOS)), 4.0); bw /= (bw.x + bw.y + bw.z);
                    half d = SAMPLE_TEXTURE2D(_Detail, sampler_Detail, p.zy).r * bw.x + SAMPLE_TEXTURE2D(_Detail, sampler_Detail, p.xz).r * bw.y + SAMPLE_TEXTURE2D(_Detail, sampler_Detail, p.xy).r * bw.z;
                    albedo *= lerp(1.0, d * 2.0, _DetailAmt);
                    // relief from the matching normal maps (mip + anisotropic filtered), blended across the three projections
                    float k = _DetailBump * 1.6;
                    float2 tx = (SAMPLE_TEXTURE2D(_DetailN, sampler_DetailN, p.zy).rg * 2.0 - 1.0) * bw.x * k;
                    float2 ty = (SAMPLE_TEXTURE2D(_DetailN, sampler_DetailN, p.xz).rg * 2.0 - 1.0) * bw.y * k;
                    float2 tz = (SAMPLE_TEXTURE2D(_DetailN, sampler_DetailN, p.xy).rg * 2.0 - 1.0) * bw.z * k;
                    float3 nOS = normalize(i.normalOS);
                    nOS += float3(ty.x + tz.x, tx.y + tz.y, tx.x + ty.y);
                    N = normalize(TransformObjectToWorldNormal(nOS));
                }
                float2 screenUV = GetNormalizedScreenSpaceUV(i.positionCS);

                half aoDirect = 1, aoIndirect = 1;
                #if defined(_SCREEN_SPACE_OCCLUSION)
                    AmbientOcclusionFactor ao = GetScreenSpaceAmbientOcclusion(screenUV);
                    aoDirect = ao.directAmbientOcclusion; aoIndirect = ao.indirectAmbientOcclusion;
                #endif

                Light mainLight = GetMainLight(TransformWorldToShadowCoord(i.positionWS), i.positionWS, half4(1, 1, 1, 1));    // includes drifting cloud shadows (light cookie)
                half ndl = dot(N, mainLight.direction);
                half ramp = smoothstep(0.22, 0.70, ndl * 0.5 + 0.5);                 // soft, slightly stylised terminator
                half lit = ramp * mainLight.shadowAttenuation * aoDirect;

                half3 ambient = lerp(_NamGround.rgb, _NamSky.rgb, N.y * 0.5 + 0.5) * aoIndirect;
                half3 col = albedo * (ambient + mainLight.color * lit);
                // warm band along the terminator: light seems to soak into the surface a little
                col += albedo * half3(1.0, 0.42, 0.22) * (ramp * (1.0 - ramp)) * mainLight.shadowAttenuation * 0.55;

                // glossy highlight
                half3 H = normalize(mainLight.direction + V);
                half spec = pow(saturate(dot(N, H)), exp2(_Smoothness * 9.0 + 2.0)) * _Smoothness * _Smoothness * 1.6;
                col += mainLight.color * spec * lit;

                // fresnel rim, sky coloured, stronger on the lit side
                half rim = pow(1.0 - saturate(dot(N, V)), 3.0) * _Rim;
                col += lerp(albedo, half3(1, 1, 1), 0.35) * _NamSky.rgb * rim * (0.35 + 0.65 * lit);

                #if defined(_ADDITIONAL_LIGHTS)
                    InputData inputData = (InputData)0;
                    inputData.positionWS = i.positionWS; inputData.normalWS = N; inputData.viewDirectionWS = V; inputData.normalizedScreenSpaceUV = screenUV;
                    uint lightCount = GetAdditionalLightsCount();
                    LIGHT_LOOP_BEGIN(lightCount)
                        Light l = GetAdditionalLight(lightIndex, i.positionWS);
                        half w = saturate(dot(N, l.direction) * 0.6 + 0.4);
                        col += albedo * l.color * (l.distanceAttenuation * w);
                    LIGHT_LOOP_END
                #endif

                col += _EmissionColor.rgb;
                col = MixFog(col, i.fog);
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
            float3 _LightDirection;
            float3 _LightPosition;
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            float4 vert (Attributes v) : SV_POSITION
            {
                float3 ws = WindWS(v.positionOS.xyz, v.uv);
                float3 n = TransformObjectToWorldNormal(v.normalOS);
                #if _CASTING_PUNCTUAL_LIGHT_SHADOW
                    float3 ld = normalize(_LightPosition - ws);
                #else
                    float3 ld = _LightDirection;
                #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(ws, n, ld));
                #if UNITY_REVERSED_Z
                    cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
                #else
                    cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
                #endif
                return cs;
            }
            half4 frag () : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ZWrite On ColorMask R
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            float4 vert (float4 positionOS : POSITION, float2 uv : TEXCOORD0) : SV_POSITION { return TransformWorldToHClip(WindWS(positionOS.xyz, uv)); }
            half4 frag () : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; };
            Varyings vert (Attributes v)
            {
                Varyings o;
                o.positionCS = TransformWorldToHClip(WindWS(v.positionOS.xyz, v.uv));
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                return o;
            }
            half4 frag (Varyings i) : SV_Target { return half4(normalize(i.normalWS), 0); }
            ENDHLSL
        }
    }
}
