using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// Import settings for art / models / music + project setup (URP, post-processing) + macOS (Metal) build.
public class ArtImport : AssetPostprocessor
{
    public override uint GetVersion() { return 5; }      // bump to re-import everything when these rules change

    void OnPreprocessTexture()
    {
        if (!assetPath.StartsWith("Assets/Resources/Art/") && !assetPath.StartsWith("Assets/Icon/")) return;
        var ti = (TextureImporter)assetImporter;
        string fn = Path.GetFileName(assetPath);
        bool tiling = fn.StartsWith("tex_") || fn.StartsWith("det_");
        ti.textureType = TextureImporterType.Default;
        ti.npotScale = TextureImporterNPOTScale.None;
        bool ui = fn.StartsWith("ui_") || fn.StartsWith("logo");            // drawn far below source size: needs mipmaps
        bool normal = fn.EndsWith("_n.png");
        ti.mipmapEnabled = tiling || ui;
        ti.sRGBTexture = !normal;                                            // normal maps hold vectors, not colours
        ti.alphaIsTransparency = !tiling;
        ti.wrapMode = tiling ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
        ti.filterMode = (tiling || ui) ? FilterMode.Trilinear : FilterMode.Bilinear;
        ti.anisoLevel = tiling ? 8 : 1;
        ti.textureCompression = TextureImporterCompression.Uncompressed;
        ti.maxTextureSize = 2048;
    }

    void OnPreprocessModel()
    {
        if (!assetPath.StartsWith("Assets/Resources/Models/")) return;
        var mi = (ModelImporter)assetImporter;
        mi.bakeAxisConversion = true;
        mi.importAnimation = false;
        mi.animationType = ModelImporterAnimationType.None;
        mi.importCameras = false; mi.importLights = false;
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
        mi.importNormals = ModelImporterNormals.Import;
        mi.meshCompression = ModelImporterMeshCompression.Off;
        mi.isReadable = false;
    }

    void OnPreprocessAudio()
    {
        if (!assetPath.Contains("/music_") && !assetPath.Contains("/amb_")) return;
        var ai = (AudioImporter)assetImporter;
        var s = ai.defaultSampleSettings;
        s.loadType = AudioClipLoadType.CompressedInMemory;
        s.compressionFormat = AudioCompressionFormat.Vorbis;
        s.quality = 0.9f;                                    // near-transparent Vorbis for the soundtrack
        ai.defaultSampleSettings = s;
    }
}

public static class BuildTools
{
    const string ScenePath = "Assets/Scenes/Main.unity";
    const string UrpPath = "Assets/Settings/NamURP.asset";

    static void SetupRenderPipeline()
    {
        Directory.CreateDirectory("Assets/Settings");
        var asset = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(UrpPath);
        if (asset == null)
        {
            var mi = typeof(UniversalRenderPipelineAsset).GetMethod("CreateRendererAsset", BindingFlags.NonPublic | BindingFlags.Static);
            var rd = (ScriptableRendererData)mi.Invoke(null, new object[] { UrpPath, RendererType.UniversalRenderer, true, "Renderer" });
            asset = UniversalRenderPipelineAsset.Create(rd);
            AssetDatabase.CreateAsset(asset, UrpPath);
        }
        var so = new SerializedObject(asset);
        void Set(string name, System.Action<SerializedProperty> f) { var p = so.FindProperty(name); if (p != null) f(p); else Debug.LogWarning("URP property missing: " + name); }
        Set("m_SupportsHDR", p => p.boolValue = true);
        Set("m_MSAA", p => p.intValue = 4);
        Set("m_MainLightShadowmapResolution", p => p.intValue = 4096);
        Set("m_ShadowDistance", p => p.floatValue = 90f);
        Set("m_ShadowCascadeCount", p => p.intValue = 3);
        Set("m_SoftShadowsSupported", p => p.boolValue = true);
        Set("m_SoftShadowQuality", p => p.intValue = 3);                // high: smoother shadow edges
        Set("m_AdditionalLightsRenderingMode", p => p.intValue = 1);
        Set("m_AdditionalLightsPerObjectLimit", p => p.intValue = 8);
        Set("m_RequireDepthTexture", p => p.boolValue = true);          // water: depth fade + shoreline foam
        Set("m_RequireOpaqueTexture", p => p.boolValue = true);         // water: refraction
        Set("m_SupportsLightCookies", p => p.boolValue = true);         // drifting cloud shadows
        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(asset);
        GraphicsSettings.defaultRenderPipeline = asset;
        int cur = QualitySettings.GetQualityLevel();
        for (int i = 0; i < QualitySettings.names.Length; i++) { QualitySettings.SetQualityLevel(i, false); QualitySettings.renderPipeline = asset; QualitySettings.antiAliasing = 4; }
        QualitySettings.SetQualityLevel(cur, false);

        // screen-space ambient occlusion on the renderer (soft contact shadows)
        try
        {
            var rd = AssetDatabase.LoadAssetAtPath<ScriptableRendererData>("Assets/Settings/NamURP_Renderer.asset");
            var ssaoType = typeof(UniversalRenderPipelineAsset).Assembly.GetType("UnityEngine.Rendering.Universal.ScreenSpaceAmbientOcclusion");
            if (rd != null && ssaoType != null && !rd.rendererFeatures.Exists(f => f != null && f.GetType() == ssaoType))
            {
                var f = (ScriptableRendererFeature)ScriptableObject.CreateInstance(ssaoType);
                f.name = "SSAO";
                AssetDatabase.AddObjectToAsset(f, rd);
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(f, out string _, out long localId);
                var rso = new SerializedObject(rd);
                var list = rso.FindProperty("m_RendererFeatures"); list.arraySize++; list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = f;
                var map = rso.FindProperty("m_RendererFeatureMap"); map.arraySize++; map.GetArrayElementAtIndex(map.arraySize - 1).longValue = localId;
                rso.ApplyModifiedPropertiesWithoutUndo();
                var fso = new SerializedObject(f);
                void FS(string n, System.Action<SerializedProperty> a) { var p = fso.FindProperty(n); if (p != null) a(p); else Debug.LogWarning("SSAO property missing: " + n); }
                FS("m_Settings.Intensity", p => p.floatValue = 1.5f); FS("m_Settings.Radius", p => p.floatValue = 0.45f);
                FS("m_Settings.DirectLightingStrength", p => p.floatValue = 0.35f); FS("m_Settings.Falloff", p => p.floatValue = 60f);
                fso.ApplyModifiedPropertiesWithoutUndo();
                EditorUtility.SetDirty(rd);
                Debug.Log("SSAO feature added");
            }
        }
        catch (System.Exception e) { Debug.LogWarning("SSAO setup skipped: " + e.Message); }

        // base materials (keeps the needed URP Lit variants in the build)
        Directory.CreateDirectory("Assets/Resources/Mats");
        var lit = Shader.Find("Universal Render Pipeline/Lit");
        if (AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/Mats/Lit.mat") == null)
            AssetDatabase.CreateAsset(new Material(lit), "Assets/Resources/Mats/Lit.mat");
        if (AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/Mats/LitEmis.mat") == null)
        {
            var m = new Material(lit);
            m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.white); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            AssetDatabase.CreateAsset(m, "Assets/Resources/Mats/LitEmis.mat");
        }

        // post-processing profile
        const string vp = "Assets/Resources/NamVolume.asset";
        AssetDatabase.DeleteAsset(vp);
        var prof = ScriptableObject.CreateInstance<VolumeProfile>();
        AssetDatabase.CreateAsset(prof, vp);
        T Add<T>() where T : VolumeComponent { var c = prof.Add<T>(true); c.hideFlags = HideFlags.HideInInspector | HideFlags.HideInHierarchy; AssetDatabase.AddObjectToAsset(c, prof); return c; }
        var bloom = Add<Bloom>(); bloom.threshold.value = 0.92f; bloom.intensity.value = 0.95f; bloom.scatter.value = 0.76f; bloom.highQualityFiltering.value = true; bloom.tint.value = new Color(1f, 0.95f, 0.88f);
        var tm = Add<Tonemapping>(); tm.mode.value = TonemappingMode.Neutral;
        var ca = Add<ColorAdjustments>(); ca.postExposure.value = 0.08f; ca.contrast.value = 14f; ca.saturation.value = 22f;
        var st = Add<SplitToning>(); st.shadows.value = new Color(0.42f, 0.52f, 0.72f); st.highlights.value = new Color(0.78f, 0.66f, 0.46f); st.balance.value = 10f;
        var vg = Add<Vignette>(); vg.intensity.value = 0.27f; vg.smoothness.value = 0.5f; vg.color.value = new Color(0.12f, 0.05f, 0.2f);
        var dof = Add<DepthOfField>(); dof.mode.value = DepthOfFieldMode.Bokeh; dof.focusDistance.value = 21.3f; dof.focalLength.value = 120f; dof.aperture.value = 2.6f; dof.bladeCount.value = 7;
        var wb = Add<WhiteBalance>(); wb.temperature.value = 9f;
        var chr = Add<ChromaticAberration>(); chr.intensity.value = 0.07f;
        EditorUtility.SetDirty(prof);
    }

    [MenuItem("Nam/Setup Project")]
    public static void Setup()
    {
        if (!File.Exists(ScenePath))
        {
            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, ScenePath);
        }
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };

        PlayerSettings.productName = "Nam's Adventures";
        PlayerSettings.companyName = "Nam Studio";
        PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Standalone, "com.namstudio.namsadventures");
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneOSX, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneOSX, new[] { GraphicsDeviceType.Metal });
        PlayerSettings.colorSpace = ColorSpace.Linear;
        PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
        PlayerSettings.defaultIsNativeResolution = true;
        PlayerSettings.resizableWindow = true;
        PlayerSettings.SplashScreen.show = false;
        PlayerSettings.macRetinaSupport = true;
        SetupRenderPipeline();

        var icon = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Icon/icon_1024.png");
        if (icon != null)
        {
            PlayerSettings.SetIcons(NamedBuildTarget.Unknown, new[] { icon }, IconKind.Any);
            int n = PlayerSettings.GetIconSizes(NamedBuildTarget.Standalone, IconKind.Any).Length;
            var arr = new Texture2D[n];
            for (int i = 0; i < n; i++) arr[i] = icon;
            PlayerSettings.SetIcons(NamedBuildTarget.Standalone, arr, IconKind.Any);
        }
        else Debug.LogError("Icon missing");
        AssetDatabase.SaveAssets();
    }

    [MenuItem("Nam/Build macOS App")]
    public static void BuildMac()
    {
        Setup();
        var opts = new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = "Build/Nam's Adventures.app",
            target = BuildTarget.StandaloneOSX,
            options = BuildOptions.None,
        };
        var report = BuildPipeline.BuildPlayer(opts);
        Debug.Log("BUILD_RESULT " + report.summary.result + " errors=" + report.summary.totalErrors + " size=" + report.summary.totalSize);
        if (Application.isBatchMode) EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
    }
}
