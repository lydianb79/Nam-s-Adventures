// Full-screen iris wipe for the UI: everything outside a circle is covered, with a gold rim on the edge.
Shader "Nam/Iris"
{
    Properties
    {
        _Color ("Cover colour", Color) = (0.08, 0.02, 0.12, 1)
        _Rim ("Rim colour", Color) = (1, 0.78, 0.25, 1)
        _Center ("Centre (viewport)", Vector) = (0.5, 0.5, 0, 0)
        _Radius ("Radius (screen heights)", Float) = 1
        _Aspect ("Aspect", Float) = 1.777
    }
    SubShader
    {
        Tags { "Queue"="Overlay" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Cull Off ZWrite Off ZTest Always
        Blend SrcAlpha OneMinusSrcAlpha
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
            fixed4 _Color, _Rim; float4 _Center; float _Radius, _Aspect;
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv; return o; }
            fixed4 frag (v2f i) : SV_Target
            {
                float2 d = i.uv - _Center.xy; d.x *= _Aspect;
                float dist = length(d);
                float a = smoothstep(_Radius, _Radius + 0.006, dist);
                float rim = 1.0 - smoothstep(_Radius + 0.012, _Radius + 0.03, dist);
                return fixed4(lerp(_Color.rgb, _Rim.rgb, rim), a);
            }
            ENDCG
        }
    }
}
