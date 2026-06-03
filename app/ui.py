"""
UI module: contains `create_ui(app)` which builds the Gradio interface.
This module intentionally avoids importing the application class to prevent
circular imports; `app` is passed in at runtime.
"""
from typing import Any
import gradio as gr
from pathlib import Path



def create_ui(app: Any) -> gr.Blocks:
    """Build and return the Gradio Blocks interface for the app.
    """
    example_dir = Path(__file__).resolve().parent / "assets" / "examples"

    with gr.Blocks(
        title="Image-to-Goods 🔑",
        theme=gr.themes.Base(),
        css="""
        /* 국대 픽셀 폰트 '둥근모(DungGeunMo)' 불러오기 */
        @import url('https://cdn.jsdelivr.net/gh/Dalgona/neodgm-webfont@1.530/neodgm/style.css');

        :root {
            /* Gradio의 숨겨진 모든 기본 배경색 변수를 칠흑색으로 고정 */
            --bg: #000000 !important; 
            --background-fill-primary: #000000 !important;
            --background-fill-secondary: #000000 !important;
            --block-background-fill: #000000 !important;
            --container-background-fill: #000000 !important;
            --input-background-fill: #000000 !important;
            --panel-bg: transparent; 
            
            /* 네온 그린 및 글로우 효과 */
            --accent: #39ff14; 
            --text: #39ff14;
            --muted-text: #1b7a0b; 
            --border: #39ff14;
            --neon-glow: 0 0 10px rgba(57, 255, 20, 0.6);
        }

        html, body, .gradio-container {
            font-family: 'NeoDunggeunmo', monospace !important;
            background-color: var(--bg) !important;
            color: var(--text) !important;
            
            /* CRT 모니터 스캔라인 효과 */
            background-image: linear-gradient(rgba(0, 0, 0, 0) 50%, rgba(0, 0, 0, 0.4) 50%) !important;
            background-size: 100% 4px !important;
            letter-spacing: 1px;
            text-shadow: var(--neon-glow);
        }

        /* 🌟 [핵심 수정] Gradio 내부 컴포넌트(에디터 툴바, 3D 캔버스, 플롯 변수)의 숨겨진 흰색 배경 강제 제거 */
        .gradio-container *, 
        .image-editor, .image-container, .canvas-wrap, canvas,
        .plot-container, .gltf-viewer, .model3d-container,
        div[class*="builtin-theme"], div[class*="image-window"], .subform {
            background-color: #000000 !important;
            background: #000000 !important;
            border-color: var(--border) !important;
        }

        .gradio-container .wrap {
            max-width: 1200px !important;
            margin: 12px auto !important;
            padding: 20px !important;
        }

        /* 헤더 타이틀 */
        .title-header-container {
            display: flex; justify-content: center; align-items: center;
            padding: 30px 0 30px 0; margin-bottom: 20px;
        }
        .title-cap-row { display: flex; gap: 16px; justify-content: center; align-items: center; flex-wrap: wrap; }
        .title-cap {
            background: #000000; color: var(--text); padding: 12px 24px; font-size: 26px;
            text-transform: uppercase; border: 3px solid var(--border);
            box-shadow: 6px 6px 0px var(--border), inset 0 0 15px rgba(57,255,20,0.2);
            text-shadow: var(--neon-glow);
        }
        .title-cap.small { padding: 12px 16px; min-width: 50px; font-size: 26px; }

        /* Step Panels */
        .step-panel { 
            padding: 24px; background: transparent !important; margin-bottom: 30px; 
            border: 2px dashed var(--border) !important; 
            box-shadow: inset 0 0 20px rgba(57,255,20,0.05) !important; 
        }
        .step-kicker { 
            display: inline-block; padding: 6px 12px; font-size: 16px; 
            background: #000000; color: var(--text); margin-bottom: 16px;
            border: 2px solid var(--border); box-shadow: 4px 4px 0px var(--border);
            text-shadow: var(--neon-glow);
        }
        .step-title { margin: 0 0 20px 0 !important; font-size: 24px; color: var(--text); text-shadow: var(--neon-glow); }
        .field-helper { color: var(--muted-text); font-size: 14px; margin-top: 8px; text-shadow: none; }
        /* 상태창 '내부 출력 텍스트' 강제 변경 (읽기 전용 텍스트박스 방어) */
        .status-content-only textarea, 
        .status-content-only input {
            color: var(--muted-text) !important;
            -webkit-text-fill-color: var(--muted-text) !important; /* 브라우저 강제 적용 */
            text-shadow: none !important;
        }
        /* Input Styles */
        .control-box input, .control-box textarea, .control-box select {
            background: #000000 !important; border: 2px solid var(--border) !important;
            padding: 14px !important; color: var(--text) !important;
            font-family: 'NeoDunggeunmo', monospace !important; font-size: 16px !important;
            box-shadow: 0 0 8px rgba(57,255,20,0.2) !important; text-shadow: var(--neon-glow);
        }
        .control-box input:focus, .control-box textarea:focus {
            background: #001a00 !important; outline: none !important; border-width: 3px !important;
            box-shadow: 0 0 15px rgba(57,255,20,0.5) !important;
        }

        /* 기본 기능 버튼들 */
        .gradio-container .gr-button, .gradio-container button { 
            border-radius: 0px !important; padding: 12px 20px !important; font-size: 18px !important;
            font-family: 'NeoDunggeunmo', monospace !important; background: #000000 !important; 
            color: var(--text) !important; border: 2px solid var(--border) !important;
            box-shadow: 6px 6px 0px var(--border), 0 0 10px rgba(57,255,20,0.3) !important;
            transition: none !important; text-transform: uppercase; text-shadow: var(--neon-glow);
        }
        .gradio-container .gr-button:active, .gradio-container button:active {
            transform: translate(6px, 6px) !important;
            box-shadow: 0px 0px 0px var(--border), 0 0 20px rgba(57,255,20,0.8) !important; 
        }
        .gradio-container .gr-button.primary { 
            background: var(--text) !important; color: #000000 !important; font-weight: 900 !important;
            text-shadow: none !important; box-shadow: 6px 6px 0px #1b7a0b, 0 0 15px rgba(57,255,20,0.5) !important;
            border-color: var(--text) !important;
        }

        /* 레트로 기계식 키보드 방향키 스타일 */
        .nav-key-btn {
            background: #000000 !important;
            color: var(--text) !important;
            font-size: 22px !important;
            font-weight: 900 !important;
            border-top: 2px solid var(--border) !important;
            border-left: 2px solid var(--border) !important;
            border-bottom: 10px solid var(--muted-text) !important;
            border-right: 8px solid var(--muted-text) !important;
            border-radius: 8px !important; 
            padding: 16px 40px !important;
            box-shadow: 0 15px 25px rgba(57,255,20,0.15) !important;
            width: 100%;
        }
        .nav-key-btn:active {
            border-bottom: 2px solid var(--border) !important;
            border-right: 2px solid var(--border) !important;
            transform: translate(8px, 8px) !important;
            box-shadow: 0 0 20px rgba(57,255,20,0.9) !important;
            background: #001a00 !important; 
        }

        /* Image containment */
        .contain-image img { object-fit: contain !important; max-height: 140px !important; background: transparent !important; }
        .example-image img { object-fit: contain !important; max-height: 180px !important; background: transparent !important; }

        /* Sliders & Checkboxes */
        input[type=range] { height: 6px; background: var(--muted-text); }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none; width: 14px; height: 28px; background: var(--text); margin-top: -11px;
        }
        input[type=checkbox] { border: 2px solid var(--border); background-color: #000; }
        input[type=checkbox]:checked { background-color: var(--text) !important; border-color: var(--text) !important; }

        .result-box, .result-box .form, .result-box .block, .result-box .padded { background: transparent !important; border: none !important; box-shadow: none !important; }
        label, span.svelte-1gfkn6j { color: var(--text) !important; font-family: 'NeoDunggeunmo', monospace !important; text-shadow: var(--neon-glow); }
        .gradio-container .gr-skip, .gradio-container .footer, .gradio-container footer { display:none !important; }
        
        /* 🌟 드롭다운(선택창) 목록 스타일 강제 적용 */
        ul.options, .options, .dropdown-options {
            background-color: #000000 !important;
            border: 2px solid var(--border) !important;
            box-shadow: 0 0 15px rgba(57,255,20,0.3) !important;
        }
        
        /* 드롭다운 내부 기본 항목들 */
        ul.options li, .options li, .options .item {
            color: var(--text) !important;
            background-color: #000000 !important;
            font-family: 'NeoDunggeunmo', monospace !important;
            text-shadow: var(--neon-glow) !important;
            font-size: 16px !important;
            padding: 10px !important;
        }
        
        /* 마우스 올렸을 때(Hover) & 선택된 항목 강조 */
        ul.options li:hover, .options li:hover, ul.options li.selected, .options li.selected {
            background-color: #001a00 !important; /* 살짝 짙은 초록 배경 */
            color: var(--text) !important;
            text-shadow: 0 0 20px rgba(57,255,20,0.9) !important;
            font-weight: bold !important;
        }
        """
    ) as interface:

        # 맨 위 제목
        gr.HTML(
            """
            <div class="title-header-container">
                <div class="title-cap-row">
                    <div class="title-cap">image</div>
                    <div class="title-cap">to</div>
                    <div class="title-cap">keycap</div>
                    <div class="title-cap small">🐶</div>
                    <div class="title-cap small">🐱</div>
                </div>
            </div>
            """
        )

        # PAGE 1: 아이디어 입력 & 이미지 생성
        with gr.Column(visible=True) as page_1:
            with gr.Group(elem_classes=["step-panel", "step-light"]):
                gr.HTML("<div class='step-kicker'>C:\> PAGE 1</div><h2 class='step-title'>아이디어 입력 & 이미지 생성</h2>")

                with gr.Row(equal_height=True):
                    with gr.Column(scale=5, elem_classes=["control-box"]):
                        concept_input = gr.Textbox(label="[ 만들고 싶은 디자인 묘사 ]", placeholder="예: 귀여운 강아지 등...", lines=3)
                        with gr.Row():
                            generate_btn = gr.Button("🎨 이미지 생성 (Run)", variant="primary", size="lg")
                            upload_btn = gr.UploadButton(label="디스크에서 업로드", file_types=["image"])

                        initial_samples, _ = app.get_sample_list(max_slots=3)
                        sample_state = gr.State(value=initial_samples)
            
                        sample_load_buttons = []
                        with gr.Row():
                            for i in range(3):
                                with gr.Column(scale=1):
                                    path = initial_samples[i] if initial_samples and i < len(initial_samples) else None
                                    thumb = gr.Image(value=path, label=f"SAMPLE_{i+1}", interactive=False,  elem_classes=["contain-image"])
                                    btn = gr.Button("불러오기")
                                    sample_load_buttons.append(btn)

                    with gr.Column(scale=7, elem_classes=["result-box", "result-stack"]):
                        # 🌟 [수정됨] gr.ImageEditor -> gr.Image로 변경 및 크롭 버튼 제거
                        image_output = gr.Image(label="[ 생성/업로드된 이미지 ]", type="pil", interactive=False)
                        image_status = gr.Textbox(label="상태", interactive=False, visible=False, elem_classes=["status-content-only"])
                        download_current_image = gr.DownloadButton(label="📥 이미지 저장")

            with gr.Row():
                gr.Column(scale=2)
                btn_next_1 = gr.Button("NEXT ► [ 3D 폴리곤 생성으로 이동 ]", elem_classes=["nav-key-btn"])
                gr.Column(scale=2)

        # PAGE 2: 3D 폴리곤 생성
        with gr.Column(visible=False) as page_2:
            with gr.Group(elem_classes=["step-panel", "step-light"]):
                gr.HTML("<div class='step-kicker'>C:\> PAGE 2</div><h2 class='step-title'>3D 폴리곤 빌드</h2>")

                with gr.Row(equal_height=True):
                    with gr.Column(scale=4, elem_classes=["control-box"]):
                        marching_cubes = gr.Slider(minimum=32, maximum=320, value=256, step=16, label="해상도(Resolution)")
                        marching_helper = gr.HTML("<div class='field-helper'>// 높을수록 세부 표현이 좋으나 렌더링 시간 증가</div>")
                        remove_bg = gr.Checkbox(label="배경 투명화 (알파 채널)", value=True, interactive=True)
                        mesh_btn = gr.Button("🌐 3D 메시 빌드", variant="primary", size="lg")

                    with gr.Column(scale=8, elem_classes=["result-box", "result-stack"]):
                        mesh_viewer = gr.Model3D(label="[ 3D 렌더링 뷰어 ]")
                        mesh_status = gr.Textbox(label="시스템 상태", interactive=False, elem_classes=["status-content-only"])
                        with gr.Row():
                            download_original_glb = gr.DownloadButton(label="📥 원본(.glb) 다운로드")
                            download_original_obj = gr.DownloadButton(label="📥 원본(.obj) 다운로드")
            
            with gr.Row():
                btn_prev_2 = gr.Button("◄ PREV [ 돌아가기 ]", elem_classes=["nav-key-btn"])
                btn_next_2 = gr.Button("NEXT ► [ 최종 조립으로 이동 ]", elem_classes=["nav-key-btn"])

        # PAGE 3: 최종 조립 & 시스템 종료
        with gr.Column(visible=False) as page_3:
            with gr.Group(elem_classes=["step-panel", "step-dark"]):
                gr.HTML("<div class='step-kicker'>C:\> PAGE 3</div><h2 class='step-title'>조립 & 시스템 종료</h2>")

                with gr.Row(equal_height=True):
                    with gr.Column(scale=4, elem_classes=["control-box"]):
                        orientation_dropdown = gr.Dropdown(choices=list(app.ORIENTATION_PRESETS.keys()), value=app.DEFAULT_ORIENTATION_PRESET, label="축 방향 프리셋")
                        gr.HTML("<div class='field-helper'>// 기본값은 '후면' 프리셋 (사용자 쪽을 바라봄).</div>")
                        merge_btn = gr.Button("🧩 하부와 결합 (Compile)", variant="primary", size="lg")

                    with gr.Column(scale=8, elem_classes=["result-box", "result-stack"]):
                        merged_viewer = gr.Model3D(label="[ 최종 3D 빌드 뷰어 ]")
                        merged_status = gr.Textbox(label="빌드 상태", interactive=False, elem_classes=["status-content-only"])
                        with gr.Row():
                            download_final_glb = gr.DownloadButton(label="📥 최종본(.glb) 다운로드")
                            download_final_obj = gr.DownloadButton(label="📥 최종본(.obj) 다운로드")

            with gr.Group(elem_classes=["step-panel", "step-light"]):
                gr.HTML("<div class='step-kicker'>C:\> HELP</div><h2 class='step-title'>메뉴얼.TXT</h2>")
                with gr.Row(equal_height=True):
                    with gr.Column(scale=6, elem_classes=["control-box"]):
                        gr.HTML("<div style='font-size: 1.2rem; margin-bottom: 0.5rem; color: var(--text);'>[1. 키보드 꾸미기]</div><div class='field-helper'>// 3D 프린터 -> 키축 위에 직접 꽂기</div>")
                        gr.Image(value=str(example_dir / "example.png"), label="예시 화면_01", interactive=False, elem_classes=["example-image"])
                    with gr.Column(scale=6, elem_classes=["control-box"]):
                        gr.HTML("<div style='font-size: 1.2rem; margin-bottom: 0.5rem; color: var(--text);'>[2. 커스텀 키링 제작]</div><div class='field-helper'>// 하단부 + 키축과 결합 -> 커스텀 클리커 완성</div>")
                        gr.Image(value=str(example_dir / "example2.png"), label="예시 화면_02", interactive=False, elem_classes=["example-image"])
                        download_bottom_stl = gr.DownloadButton(label="📥 키링용 하단부(.stl) 다운로드")

            with gr.Row():
                btn_prev_3 = gr.Button("◄ PREV [ 돌아가기 ]", elem_classes=["nav-key-btn"])
                gr.Column(scale=1)

        # 페이지 이동 이벤트
        def show_page_2():
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
        def show_page_3():
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
        def show_page_1():
            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

        btn_next_1.click(fn=show_page_2, inputs=[], outputs=[page_1, page_2, page_3])
        btn_prev_2.click(fn=show_page_1, inputs=[], outputs=[page_1, page_2, page_3])
        btn_next_2.click(fn=show_page_3, inputs=[], outputs=[page_1, page_2, page_3])
        btn_prev_3.click(fn=show_page_2, inputs=[], outputs=[page_1, page_2, page_3])

        # 기능 이벤트 핸들러
        generate_btn.click(fn=app.generate_image_openai, inputs=[concept_input], outputs=[image_output, image_status])
        upload_btn.upload(fn=app.upload_custom_image, inputs=[upload_btn], outputs=[image_output, image_status])
        for idx, btn in enumerate(sample_load_buttons):
            btn.click(fn=lambda paths, i=idx: app.load_sample_image_local(paths[i]) if paths and i < len(paths) and paths[i] else (None, "❌ 샘플을 찾을 수 없습니다"), inputs=[sample_state], outputs=[image_output, image_status])
        
        download_current_image.click(fn=app.download_current_image, outputs=[download_current_image])
        mesh_btn.click(fn=lambda remove_bg, marching_cubes: app.generate_3d_mesh(remove_background=remove_bg, foreground_ratio=0.85, marching_cubes_resolution=marching_cubes, target_height_mm=100), inputs=[remove_bg, marching_cubes], outputs=[mesh_status, mesh_viewer])
        merge_btn.click(fn=lambda preset: app.merge_solid_mesh_with_base_keycap(0.5, preset, app.DEFAULT_ORIENTATION_AXIS, app.DEFAULT_UPRIGHT_TARGET_AXIS, app.DEFAULT_XY_ALIGNMENT_MODE), inputs=[orientation_dropdown], outputs=[merged_viewer, merged_status])
        download_final_glb.click(fn=app.download_final_glb, outputs=[download_final_glb])
        download_final_obj.click(fn=app.download_final_obj, outputs=[download_final_obj])
        download_original_glb.click(fn=app.download_glb_original, outputs=[download_original_glb])
        download_original_obj.click(fn=app.download_obj_original, outputs=[download_original_obj])
        download_bottom_stl.click(fn=app.download_stl_bottom, outputs=[download_bottom_stl])

    return interface