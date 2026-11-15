// Stylised water: see-through shallows that darken with depth, wobbling refraction, sky reflection,
// sun glints, drifting sparkle lines, and foam wherever the surface meets land, boats or lotus pads.
Shader "Nam/Water"
{
    Properties
    {
        _Shallow ("Shallow", Color) = (0.30, 0.86, 0.90, 1)
        _Deep ("Deep", Color) = (0.04, 0.34, 0.62, 1)
        _Foam ("Foam", Color) = (0.95, 1, 1, 1)
        _SkyHorizon ("Sky reflection (horizon)", Color) = (0.80, 0.93, 1, 1)
        _SkyZenith ("Sky reflection (zenith)", Color) = (0.25, 0.55, 0.95, 1)
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 ws : TEXCOORD0; float fog : TEXCOORD1; float up : TEXCOORD2; };
            CBUFFER_START(UnityPerMaterial)
            half4 _Shallow; half4 _Deep; half4 _Foam; half4 _SkyHorizon; half4 _SkyZenith;
            CBUFFER_END

            float Wave(float2 p, float t)
            {
                return sin(p.x * 1.3 + t * 1.7) * 0.05 + sin(p.y * 0.9 + t * 1.1) * 0.04 + sin((p.x + p.y) * 2.6 - t * 2.3) * 0.012;
            }

            Varyings vert (Attributes v)
            {
                Varyings o;
                float3 ws = TransformObjectToWorld(v.positionOS.xyz);
                float up = step(0.5, v.normalOS.y);                      // surface (1) or the front "cut" sheet (0)
                ws.y += up * Wave(ws.xz, _Time.y);
                o.ws = ws; o.up = up;
                o.positionCS = TransformWorldToHClip(ws);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
                float t = _Time.y;
                float2 uv = GetNormalizedScreenSpaceUV(i.positionCS);
                half4 c;
                if (i.up > 0.5)
                {
                    // surface normal from the wave field plus fine ripples
                    float e = 0.08;
                    float h0 = Wave(i.ws.xz, t), hx = Wave(i.ws.xz + float2(e, 0), t), hz = Wave(i.ws.xz + float2(0, e), t);
                    float2 rip = float2(sin(i.ws.x * 7.0 + t * 2.1 + sin(i.ws.z * 5.0)) , cos(i.ws.z * 8.0 - t * 1.7 + sin(i.ws.x * 4.0))) * 0.035 * saturate(1.0 - (i.ws.z - 4.0) / 30.0);
                    float3 n = normalize(float3(-(hx - h0) / e - rip.x, 1.0, -(hz - h0) / e - rip.y));
                    float3 V = normalize(GetWorldSpaceViewDir(i.ws));

                    // how much water lies between the surface and whatever is behind it
                    float surf = LinearEyeDepth(i.positionCS.z, _ZBufferParams);
                    float2 ruv = uv + n.xz * 0.03;
                    float sceneR = LinearEyeDepth(SampleSceneDepth(ruv), _ZBufferParams);
                    if (sceneR < surf) ruv = uv;                               // do not pull in things in front of the water
                    float thick = max(0, LinearEyeDepth(SampleSceneDepth(ruv), _ZBufferParams) - surf);
                    float edge = max(0, LinearEyeDepth(SampleSceneDepth(uv), _ZBufferParams) - surf);

                    half3 under = SampleSceneColor(ruv);
                    float fade = 1.0 - exp(-thick * 0.22);
                    half3 body = lerp(under * lerp(half3(1, 1, 1), _Shallow.rgb, 0.55), lerp(_Shallow.rgb, _Deep.rgb, saturate(thick * 0.07)), fade);

                    // sky reflection, stronger at grazing angles
                    float3 r = reflect(-V, n);
                    half3 sky = lerp(_SkyHorizon.rgb, _SkyZenith.rgb, saturate(r.y * 1.6));
                    float fres = 0.04 + 0.36 * pow(1.0 - saturate(dot(n, V)), 3.0);
                    half3 col = lerp(body, sky, fres);

                    Light L = GetMainLight(TransformWorldToShadowCoord(i.ws), i.ws, half4(1, 1, 1, 1));
                    col *= lerp(0.72, 1.0, L.shadowAttenuation);
                    // sun glints + stylised sparkle streaks
                    float spec = pow(saturate(dot(reflect(-L.direction, n), V)), 180.0) * 2.5 * L.shadowAttenuation;
                    float w = sin(i.ws.x * 2.1 + sin(i.ws.z * 1.7 + t) * 1.5 + t * 0.8) * sin(i.ws.z * 3.3 - t * 0.6 + sin(i.ws.x * 0.7) * 2.0);
                    float far = saturate((i.ws.z + 2.0) / 60.0);
                    col += L.color * spec + _Foam.rgb * smoothstep(0.88, 0.97, w) * (1.0 - far) * 0.55;

                    // foam where the water touches something, with a wobbling edge
                    float fn = sin(i.ws.x * 9.0 + t * 1.3) * sin(i.ws.z * 11.0 - t * 1.1) * 0.5 + 0.5;
                    float foam = smoothstep(0.34 + fn * 0.22, 0.0, edge) + smoothstep(0.75, 0.55, edge) * smoothstep(0.55, 0.75, sin(edge * 22.0 - t * 3.0) * 0.5 + 0.5) * 0.45;
                    col = lerp(col, _Foam.rgb, saturate(foam));
                    c = half4(col, 1);
                }
                else
                {
                    // the vertical cut in front of the ground: tinted glass that darkens with depth, bright cap line
                    half4 s = lerp(_Shallow, _Deep, saturate((1.55 - i.ws.y) / 2.2));
                    s.a = lerp(0.70, 0.97, saturate((1.55 - i.ws.y) / 2.5));
                    float cap = smoothstep(0.1, 0.0, 1.5 - i.ws.y + sin(i.ws.x * 1.3 + t * 1.7) * 0.05);
                    s.rgb = lerp(s.rgb, _Foam.rgb, cap);
                    float ray = smoothstep(0.6, 1.0, sin(i.ws.x * 1.7 + i.ws.y * 0.9 + t * 0.7)) * saturate((i.ws.y + 1.0) / 2.5) * 0.12;
                    s.rgb += ray;
                    c = s;
                }
                c.rgb = MixFog(c.rgb, i.fog);
                return c;
            }
            ENDHLSL
        }
    }
}
