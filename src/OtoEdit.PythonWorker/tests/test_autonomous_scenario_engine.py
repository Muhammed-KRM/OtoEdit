"""
5 Aşamalı Otonom Kurgu Senaryosu Motoru (ScenarioEngine) Birim ve Entegrasyon Testleri:
1. Kullanıcının verdiği örnek metin üzerinde [geçiş] noktalarının (Tez Bitişi -> Alıntı, Yol Haritası Bitişi -> Tanım) birebir tespiti.
2. Her parçanın ayrı bir yapay zeka isteği olarak paralel değerlendirilmesi ve tekil parça çökme yalıtımı (Fault Isolation).
3. Başeditör (Critic) AI denetimi -> Düzeltme (Refiner) -> 'Başka sorun kaldı mı?' 2. kontrol onayı.
4. 3. Tur Döngü Kırıcı (Circuit Breaker) -> Kullanıcıya Sorma ve Doğal Dil Kullanıcı Revizyon Döngüsü.
"""

import json
from unittest.mock import MagicMock
from pipeline.holistic_analyzer import HolisticAnalyzer
from pipeline.scenario_engine import (
    ChunkDirector,
    ScenarioCritic,
    ScenarioMerger,
    ScenarioOrchestrator,
    ScenarioRefiner,
    SceneSegmenter,
)
from pipeline.theme_profiles import detect_theme_profile_heuristic


USER_EXAMPLE_SEGMENTS = [
    {
        "start": 0.0,
        "end": 14.0,
        "text": (
            "Değerli izleyenler, önceki dersimizde adalet nazariyesinin köklerine inmiş; "
            "'efradını câmi, ağyarını mâni' tarifiyle adaletin ne olduğunu, kâinattaki kozmik mizanı "
            "ve ferdin hakkını hiçbir zümreye feda etmeyen 'adalet-i mahza' ilkesini bütün boyutlarıyla incelemiştik."
        ),
    },
    {
        "start": 14.5,
        "end": 29.0,
        "text": (
            "Fakat tarihin ve felsefenin bize öğrettiği yalın bir hakikat var: Adalet, tek başına bir vakumun içinde yaşayamaz. "
            "Adaletin toplumsal ve bireysel hayatta nefes alabileceği yegâne iklim hürriyettir; "
            "adaleti koruyan ahlaki kalkan müsbet isyan iradesidir; "
            "adaleti ortak bir akılla ete kemiğe büründüren usul ise meşveret hukukudur."
        ),
    },
    # --- [GEÇİŞ 1 BEKLENEN NOKTA: ~29.0s - 29.5s] ---
    {
        "start": 29.5,
        "end": 46.0,
        "text": (
            "Bediüzzaman Said Nursi’nin o çarpıcı tespitiyle söylersek: 'Hürriyet, imanın bir hassasıdır.' "
            "İman bir insanda ne ölçüde inkişaf eder, kök salar ve teali ederse; o insanın hürriyete olan meyli ve izzeti de aynı nispette yükselir. "
            "İman bütün güzelliklerin, hürriyet ise bütün yüksek erdemlerin menbaıdır. "
            "Bunların tam karşısında duran istibdat, tahakküm ve zorbalık ise içtimai felaketlerin ve ahlaki çürümenin anasıdır."
        ),
    },
    {
        "start": 46.5,
        "end": 65.0,
        "text": (
            "Peki, çağımızın dillerden düşürmediği hürriyet ile İslam’ın tarif ettiği hürriyet aynı şey midir? "
            "Bir insanın hiçbir otoriteye boyun eğmemesi bir kibir midir, yoksa tevhidin kazandırdığı en saf ubudiyet ve izzet midir? "
            "Bugün; beşer hukukunun çizdiği sınırları aşarak, Thomas Hobbes’un korku felsefesinden Nurettin Topçu’nun isyan ahlakına, "
            "Kur’an’ın emrettiği meşveret nizamından kolektif aklın 111 sırrına kadar hakiki hürriyetin mimarisini inşa edeceğiz."
        ),
    },
    # --- [GEÇİŞ 2 BEKLENEN NOKTA: ~65.0s - 65.5s] ---
    {
        "start": 65.5,
        "end": 78.0,
        "text": (
            "Modern dünyanın beşerî hukuk sistemlerine baktığımızda, hürriyetin sınırını son derece pragmatik bir tarifle çizerler: "
            "'Başkalarının hak ve hürriyetine zarar vermediğin sürece dilediğini yapabilirsin.'"
        ),
    },
]


def test_user_example_paragraph_rhetorical_transitions_and_chunks():
    """
    Kullanıcının verdiği örnek metindeki 2 [geçiş] noktasının:
      1) '...meşveret hukukudur.' -> [geçiş] -> 'Bediüzzaman Said Nursi’nin o çarpıcı tespitiyle söylersek...'
      2) '...hakiki hürriyetin mimarisini inşa edeceğiz.' -> [geçiş] -> 'Modern dünyanın beşerî hukuk sistemlerine baktığımızda...'
    olarak tespit edildiğini ve videonun 3 anlamlı parçaya ayrıldığını doğrular.
    """
    analyzer = HolisticAnalyzer(enable_llm_planning=False)
    word_stream = analyzer._build_word_stream(USER_EXAMPLE_SEGMENTS)

    boundaries, _ = SceneSegmenter.detect_rhetorical_boundaries(
        word_stream=word_stream,
        video_duration=78.0,
        enable_llm=False,
    )

    assert len(boundaries) == 2
    # 1. Geçiş: ~29.25s ('hukukudur.' -> 'Bediüzzaman')
    assert 28.5 <= boundaries[0].timestamp <= 30.0
    assert "hukukudur" in boundaries[0].sentence_a_preview.lower()
    assert "bediüzzaman" in boundaries[0].sentence_b_preview.lower()

    # 2. Geçiş: ~65.25s ('inşa edeceğiz.' -> 'Modern dünyanın')
    assert 64.5 <= boundaries[1].timestamp <= 66.0
    assert "inşa edeceğiz" in boundaries[1].sentence_a_preview.lower()
    assert "modern dünyanın" in boundaries[1].sentence_b_preview.lower()

    scenes = SceneSegmenter.build_scene_chunks(word_stream, 78.0, boundaries)
    assert len(scenes) == 3
    assert scenes[0].narrative_role == "RECAP_AND_THESIS"
    assert scenes[1].narrative_role == "FOUNDATIONAL_FRAMING_AND_ROADMAP"
    assert scenes[2].narrative_role == "CONCEPT_DEFINITION"


def test_chunk_director_parallel_execution_and_fault_isolation():
    """
    Her parçanın ayrı bir yapay zeka isteği olarak paralel atıldığını ve bir parçanın
    AI isteği çöktüğünde diğer parçaların etkilenmeden tamamlandığını doğrular.
    """
    analyzer = HolisticAnalyzer(enable_llm_planning=False)
    word_stream = analyzer._build_word_stream(USER_EXAMPLE_SEGMENTS)
    boundaries, _ = SceneSegmenter.detect_rhetorical_boundaries(word_stream, 78.0, enable_llm=False)
    scenes = SceneSegmenter.build_scene_chunks(word_stream, 78.0, boundaries)
    theme = detect_theme_profile_heuristic(" ".join(s["text"] for s in USER_EXAMPLE_SEGMENTS))

    mock_gemini = MagicMock()
    mock_gemini.is_available.return_value = True

    def side_effect_generate(prompt: str, max_retries: int = 1):
        if "PARÇA #2" in prompt:
            # 2. parçanın AI çağrısı kasıtlı olarak çöksün!
            raise RuntimeError("Simulated API timeout on Chunk 2")
        if "PARÇA #1" in prompt:
            return json.dumps([
                {
                    "action_type": "DEFINITION_CALLOUT",
                    "start_word_idx": 8,
                    "end_word_idx": 13,
                    "sentence_end_word_idx": 18,
                    "text_primary": "ADALET-İ MAHZA İLKESİ",
                    "text_secondary": "Ferdin Hakkını Koruyan Mizan",
                }
            ])
        return json.dumps([
            {
                "action_type": "DEFINITION_CALLOUT",
                "start_word_idx": scenes[2].start_word_idx + 2,
                "end_word_idx": scenes[2].start_word_idx + 6,
                "sentence_end_word_idx": scenes[2].end_word_idx,
                "text_primary": "PRAGMATİK HÜRRİYET TANIMI",
                "text_secondary": "Beşerî Hukuk Sınırı",
            }
        ])

    mock_gemini.generate_text.side_effect = side_effect_generate
    mock_gemini.extract_balanced_json.side_effect = lambda raw, prefer_array=True: raw

    chunk_director = ChunkDirector(gemini_client=mock_gemini, max_workers=3)
    evaluated_scenes = chunk_director.evaluate_chunks_parallel(
        scenes=scenes,
        word_stream=word_stream,
        theme_profile=theme,
        deterministic_triggers=[],
    )

    assert len(evaluated_scenes) == 3
    # Parça 1 ve Parça 3 başarıyla AI çıktısını aldı, Parça 2 çöktüğü halde sistemi çökertmedi ('fallback' oldu)
    assert evaluated_scenes[0].status == "completed"
    assert any("ADALET-İ MAHZA" in it.text_primary for it in evaluated_scenes[0].items)
    assert evaluated_scenes[1].status == "fallback"
    assert evaluated_scenes[2].status == "completed"
    assert any("PRAGMATİK HÜRRİYET" in it.text_primary for it in evaluated_scenes[2].items)


def test_critic_refiner_loop_fixes_and_approves_on_second_check():
    """
    Başeditör (Critic) AI'ın 1. turda hataları bulup ('Şunu kaldır, şunu düzelt, şuraya şunu ekle'),
    Refiner'ın düzeltmeleri uyguladığını ve 2. turda ('Başka sorun kaldı mı?') onaylandığını doğrular.
    """
    analyzer = HolisticAnalyzer(enable_llm_planning=False)
    word_stream = analyzer._build_word_stream(USER_EXAMPLE_SEGMENTS)
    theme = detect_theme_profile_heuristic(" ".join(s["text"] for s in USER_EXAMPLE_SEGMENTS))

    mock_gemini = MagicMock()
    mock_gemini.is_available.return_value = True
    mock_gemini.extract_balanced_json.side_effect = lambda raw, prefer_array=False: raw

    critic_call_count = {"n": 0}

    def fake_generate(prompt: str, max_retries: int = 1):
        if "Başeditör (Denetçi) Yapay Zekasın" in prompt:
            critic_call_count["n"] += 1
            if critic_call_count["n"] == 1:
                return json.dumps({
                    "is_approved": False,
                    "overall_score": 72,
                    "summary_feedback": "Sahne 2'ye Nurettin Topçu eklenmeli.",
                    "revisions": [
                        {
                            "action": "ADD",
                            "scene_id": 2,
                            "action_type": "PERSON_INTRODUCTION",
                            "text_primary": "NURETTİN TOPÇU",
                            "text_secondary": "İsyan Ahlakı",
                            "wiki_query_tr": "Nurettin Topçu",
                            "reason": "Yol haritasında Nurettin Topçu vurgulanıyor.",
                        }
                    ],
                })
            # 2. Turda yapılan düzeltmeler kontrol edilir ve onaylanır
            assert "ÖNCEKİ DENETİMDEN SONRA YAPILAN DÜZELTMELER" in prompt
            return json.dumps({
                "is_approved": True,
                "overall_score": 96,
                "summary_feedback": "Tüm düzeltmeler uygulandı, başka sorun kalmadı.",
                "revisions": [],
            })
        return "[]"

    mock_gemini.generate_text.side_effect = fake_generate

    orchestrator = ScenarioOrchestrator(gemini_client=mock_gemini)
    script = orchestrator.build_and_verify_scenario(
        project_id="proj-1",
        video_id="vid-1",
        word_stream=word_stream,
        video_duration=78.0,
        theme_profile=theme,
        enable_llm=True,
    )

    assert script.iteration_count == 2
    assert script.is_approved is True
    assert script.requires_user_approval is False
    assert script.approval_status == "auto_approved"
    assert any(
        "NURETTİN TOPÇU" in it.text_primary
        for sc in script.scenes
        for it in sc.items
    )


def test_three_strike_circuit_breaker_escalates_to_user_and_applies_user_revisions():
    """
    3. denetim sonunda hâlâ sorun varsa döngünün kesilip kullanıcıya sorulduğunu
    (requires_user_approval=True) ve kullanıcının verdiği doğal dil revizyonunun
    senaryoya işlenip tekrar kullanıcı onayına sunulduğunu doğrular.
    """
    analyzer = HolisticAnalyzer(enable_llm_planning=False)
    word_stream = analyzer._build_word_stream(USER_EXAMPLE_SEGMENTS)
    theme = detect_theme_profile_heuristic(" ".join(s["text"] for s in USER_EXAMPLE_SEGMENTS))

    mock_gemini = MagicMock()
    mock_gemini.is_available.return_value = True
    mock_gemini.extract_balanced_json.side_effect = lambda raw, prefer_array=False: raw

    def always_unapproved_generate(prompt: str, max_retries: int = 1):
        if "Başeditör (Denetçi) Yapay Zekasın" in prompt:
            return json.dumps({
                "is_approved": False,
                "overall_score": 68,
                "summary_feedback": "Sahne yoğunluğu için ek düzenleme öneriliyor.",
                "revisions": [
                    {
                        "action": "ADD",
                        "scene_id": 1,
                        "action_type": "KEY_TERM_CALLOUT",
                        "text_primary": "KOZMİK MİZAN",
                        "reason": "Eksik vurgu",
                    }
                ],
            })
        return "[]"

    mock_gemini.generate_text.side_effect = always_unapproved_generate

    orchestrator = ScenarioOrchestrator(gemini_client=mock_gemini)
    script = orchestrator.build_and_verify_scenario(
        project_id="proj-loop",
        video_id="vid-loop",
        word_stream=word_stream,
        video_duration=78.0,
        theme_profile=theme,
        enable_llm=True,
    )

    # Tam 3. seferden sonra döngü kırılır ve kullanıcıya sorulur!
    assert script.iteration_count == 3
    assert script.is_approved is False
    assert script.requires_user_approval is True
    assert script.approval_status == "awaiting_user"
    assert "Bu senaryoyu uygulayalım mı" in script.last_critic_message

    # Şimdi kullanıcı senaryoyu beğenmeyip doğal dille revize verir:
    refiner = ScenarioRefiner(gemini_client=None)
    updated_script, changes = refiner.apply_user_natural_language_feedback(
        script=script,
        user_feedback="3. parçaya 'BEŞERÎ HUKUK SINIRI' başlığı ekle, 'KOZMİK MİZAN' yazısını kaldır",
        word_stream=word_stream,
    )

    assert len(changes) >= 2
    assert updated_script.requires_user_approval is True
    assert updated_script.approval_status == "awaiting_user"
    assert "Bu halini uygulayalım mı?" in updated_script.last_critic_message
    assert any("BEŞERÎ HUKUK SINIRI" in it.text_primary for it in updated_script.scenes[2].items)
    assert not any("KOZMİK MİZAN" in it.text_primary for it in updated_script.scenes[0].items)
