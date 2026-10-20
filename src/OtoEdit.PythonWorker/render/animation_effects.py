"""OtoEdit Animation Effects - Görsel ve metin kaplamaları için animasyon hesaplamaları."""
from typing import Dict, Any, Tuple, List, Optional


class AnimationEffects:
    """Yazı ve görsel kaplamaları için FFmpeg ve ASS uyumlu animasyon parametreleri üretir."""

    @staticmethod
    def get_ass_tags(
        animation_type: str,
        duration_sec: float,
        pos_x: int = 0,
        pos_y: int = 0,
        exit_anim_type: str = "fade"
    ) -> str:
        r"""
        ASS formatı için animasyon kontrol etiketlerini döndürür.
        Giriş (entrance) ve çıkış (exit) animasyonlarını kombine eder.
        Desteklenen giriş animasyonları:
          fade, pop-up, bounce, typewriter, glitch, blur-in, zoom-crash,
          slide-left, slide-right, slide-up, slide-down
        """
        duration_ms = int(duration_sec * 1000)
        anim = (animation_type or "").lower().strip()
        exit_anim = (exit_anim_type or "fade").lower().strip()

        # Çıkış fade süresi
        if exit_anim == "none":
            fade_out = 0
        elif exit_anim in ["scale-out", "pop-up"]:
            fade_out = 150
        else:
            fade_out = min(300, max(50, int(duration_ms * 0.1)))

        exit_scale_tag = ""
        if exit_anim in ["scale-out", "pop-up"]:
            exit_start = max(0, duration_ms - 250)
            exit_scale_tag = f"\\t({exit_start},{duration_ms},\\fscx40\\fscy40)"

        if anim == "fade":
            fade_in = min(300, max(50, int(duration_ms * 0.1)))
            if exit_scale_tag:
                return f"\\fad({fade_in},{fade_out}){exit_scale_tag}"
            return f"\\fad({fade_in},{fade_out})"

        elif anim == "pop-up":
            # 0-250ms arasında %50'den %100'e hızlı büyüme + hafif fade
            if exit_scale_tag:
                return f"\\fscx50\\fscy50\\t(0,250,\\fscx100\\fscy100){exit_scale_tag}\\fad(100,{fade_out})"
            return f"\\fscx50\\fscy50\\t(0,250,\\fscx100\\fscy100)\\fad(100,{fade_out})"

        elif anim == "bounce":
            # Elastik sıçrama (30% -> 115% -> 95% -> 100%)
            return (
                f"\\fscx30\\fscy30"
                f"\\t(0,180,\\fscx115\\fscy115)"
                f"\\t(180,320,\\fscx95\\fscy95)"
                f"\\t(320,450,\\fscx100\\fscy100)"
                f"{exit_scale_tag}\\fad(80,{fade_out})"
            )

        elif anim == "zoom-crash":
            # Dev boyuttan (220%) bulanık şekilde çarpıp oturma
            return (
                f"\\fscx220\\fscy220\\blur8"
                f"\\t(0,220,\\fscx100\\fscy100\\blur0)"
                f"{exit_scale_tag}\\fad(60,{fade_out})"
            )

        elif anim == "blur-in":
            # Gaussian bulanıklıktan netleşerek giriş
            return f"\\blur15\\t(0,350,\\blur0){exit_scale_tag}\\fad(150,{fade_out})"

        elif anim == "glitch":
            # Hızlı açısal ve harf aralığı titreşimi
            return (
                f"\\frz8\\fsp12"
                f"\\t(0,80,\\frz-6\\fsp-4)"
                f"\\t(80,160,\\frz4\\fsp6)"
                f"\\t(160,240,\\frz0\\fsp0)"
                f"{exit_scale_tag}\\fad(40,{fade_out})"
            )

        elif anim == "typewriter":
            # Harf aralığı daralarak / belirerek daktilo hissi
            tw_dur = min(600, max(150, int(duration_ms * 0.3)))
            return f"\\fsp25\\t(0,{tw_dur},\\fsp0){exit_scale_tag}\\fad(50,{fade_out})"

        elif anim == "slide-left":
            start_x = pos_x + 300
            anim_dur = min(400, int(duration_ms * 0.2))
            move_tag = f"\\move({start_x},{pos_y},{pos_x},{pos_y},0,{anim_dur})"
            if fade_out > 0:
                return f"{move_tag}\\fad(0,{fade_out})"
            return move_tag

        elif anim == "slide-right":
            start_x = max(0, pos_x - 300)
            anim_dur = min(400, int(duration_ms * 0.2))
            move_tag = f"\\move({start_x},{pos_y},{pos_x},{pos_y},0,{anim_dur})"
            if fade_out > 0:
                return f"{move_tag}\\fad(0,{fade_out})"
            return move_tag

        elif anim == "slide-up":
            start_y = pos_y + 200
            anim_dur = min(400, int(duration_ms * 0.2))
            move_tag = f"\\move({pos_x},{start_y},{pos_x},{pos_y},0,{anim_dur})"
            if fade_out > 0:
                return f"{move_tag}\\fad(0,{fade_out})"
            return move_tag

        elif anim == "slide-down":
            start_y = max(0, pos_y - 200)
            anim_dur = min(400, int(duration_ms * 0.2))
            move_tag = f"\\move({pos_x},{start_y},{pos_x},{pos_y},0,{anim_dur})"
            if fade_out > 0:
                return f"{move_tag}\\fad(0,{fade_out})"
            return move_tag

        # anim == "none" veya tanımsız ama exit_anim varsa
        if fade_out > 0:
            if exit_scale_tag:
                return f"{exit_scale_tag}\\fad(0,{fade_out})"
            return f"\\fad(0,{fade_out})"

        return ""

    @staticmethod
    def _build_keyframe_expr(
        keyframes: List[Dict[str, Any]],
        axis: str,
        base_dim: int,
        start_time: float,
        overlay_dim_var: str
    ) -> str:
        """
        Keyframe listesini (timeOffset, x, y) zamana bağlı parçalı doğrusal (piecewise-linear)
        FFmpeg ifadesine dönüştürür.
        """
        sorted_kfs = sorted(
            keyframes,
            key=lambda k: float(k.get("timeOffset") if k.get("timeOffset") is not None else k.get("time", 0.0)),
        )

        # Koordinatların yüzde (0..100) mi yoksa piksel mi olduğunu belirle
        all_vals = [abs(float(k.get(axis, 50.0))) for k in sorted_kfs]
        is_percentage = all(v <= 100.0 for v in all_vals)

        points: List[Tuple[float, int]] = []
        for k in sorted_kfs:
            t_off = float(k.get("timeOffset") if k.get("timeOffset") is not None else k.get("time", 0.0))
            raw_v = float(k.get(axis, 50.0))
            px_v = int(round((raw_v / 100.0) * base_dim)) if is_percentage else int(round(raw_v))
            points.append((round(start_time + t_off, 3), px_v))

        if len(points) == 1:
            return f"({points[0][1]}-({overlay_dim_var}/2))"

        # Sondan başa iç içe if(lt(t, t_next), lerp, ...) inşa et
        expr = f"{points[-1][1]}"
        for i in range(len(points) - 2, -1, -1):
            t0, p0 = points[i]
            t1, p1 = points[i + 1]
            dt = max(0.01, round(t1 - t0, 3))
            lerp = f"({p0}+({p1}-{p0})*((t-{t0})/{dt}))"
            if i == 0:
                expr = f"if(lt(t,{t0}),{p0},if(lt(t,{t1}),{lerp},{expr}))"
            else:
                expr = f"if(lt(t,{t1}),{lerp},{expr})"

        return f"(({expr})-({overlay_dim_var}/2))"

    @staticmethod
    def get_ffmpeg_overlay_coords(
        position: Any,
        base_w: int = 1920,
        base_h: int = 1080,
        anim_type: str = "fade",
        start_time: float = 0.0,
        duration: float = 5.0,
        loop_anim: Optional[str] = None,
        keyframes: Optional[List[Dict[str, Any]]] = None,
        pos_x: Optional[float] = None,
        pos_y: Optional[float] = None,
        **kwargs
    ) -> Tuple[str, str]:
        """
        FFmpeg filter_complex overlay filtresi için x ve y matematiksel ifadelerini döndürür.
        Giriş animasyonları (slide-*, pop-up, bounce, zoom-crash),
        döngü animasyonları (pulse, float, wiggle, shake, pendulum) ve
        keyframe interpolasyonunu destekler.
        """
        loop_clean = str(kwargs.get("loopAnimation") or loop_anim or "none").lower().strip()
        anim = (anim_type or "").lower().strip()

        # 1. Keyframe varsa parçalı doğrusal (piecewise-linear) yörünge üret
        if keyframes and isinstance(keyframes, list) and len(keyframes) > 0:
            x_expr = AnimationEffects._build_keyframe_expr(keyframes, "x", base_w, start_time, "overlay_w")
            y_expr = AnimationEffects._build_keyframe_expr(keyframes, "y", base_h, start_time, "overlay_h")
        else:
            if pos_x is not None and pos_y is not None:
                cx = int(round((float(pos_x) / 100.0) * base_w))
                cy = int(round((float(pos_y) / 100.0) * base_h))
                target_x = f"{cx}-(overlay_w/2)"
                target_y = f"{cy}-(overlay_h/2)"
            else:
                target_x, target_y = AnimationEffects.resolve_static_position(position, base_w, base_h)

            x_expr, y_expr = target_x, target_y

            # 2. Giriş (Entrance) Animasyonları
            if anim == "slide-left":
                anim_duration = 0.4
                x_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"main_w - (main_w - ({target_x})) * ((t - {start_time}) / {anim_duration}), "
                    f"{target_x})"
                )
            elif anim == "slide-right":
                anim_duration = 0.4
                x_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"-overlay_w + ({target_x} + overlay_w) * ((t - {start_time}) / {anim_duration}), "
                    f"{target_x})"
                )
            elif anim == "slide-up":
                anim_duration = 0.4
                y_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"main_h - (main_h - ({target_y})) * ((t - {start_time}) / {anim_duration}), "
                    f"{target_y})"
                )
            elif anim == "slide-down":
                anim_duration = 0.4
                y_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"-overlay_h + ({target_y} + overlay_h) * ((t - {start_time}) / {anim_duration}), "
                    f"{target_y})"
                )
            elif anim == "pop-up":
                anim_duration = 0.25
                y_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"({target_y}) + 32 * (1 - ((t - {start_time}) / {anim_duration})), "
                    f"{target_y})"
                )
            elif anim == "bounce":
                anim_duration = 0.55
                y_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"({target_y}) - 48 * abs(sin(2*PI*(t - {start_time})/0.35)) * (1 - ((t - {start_time}) / {anim_duration})), "
                    f"{target_y})"
                )
            elif anim == "zoom-crash":
                anim_duration = 0.30
                x_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"({target_x}) + 14 * sin(16*PI*(t - {start_time})) * (1 - ((t - {start_time}) / {anim_duration})), "
                    f"{target_x})"
                )
                y_expr = (
                    f"if(lt(t, {start_time + anim_duration}), "
                    f"({target_y}) - 55 * (1 - ((t - {start_time}) / {anim_duration})), "
                    f"{target_y})"
                )

        # 3. Sürekli Döngü (Loop) Animasyonları
        if loop_clean == "float":
            y_expr = f"({y_expr}) + 12*sin(2*PI*(t-{start_time})/1.8)"
        elif loop_clean == "pulse":
            y_expr = f"({y_expr}) + 6*sin(2*PI*(t-{start_time})/1.1)"
        elif loop_clean == "wiggle":
            x_expr = f"({x_expr}) + 10*sin(2*PI*(t-{start_time})/0.45)"
            y_expr = f"({y_expr}) + 5*cos(2*PI*(t-{start_time})/0.45)"
        elif loop_clean == "shake":
            x_expr = f"({x_expr}) + 8*sin(2*PI*(t-{start_time})/0.15)"
            y_expr = f"({y_expr}) + 8*cos(2*PI*(t-{start_time})/0.18)"
        elif loop_clean == "pendulum":
            x_expr = f"({x_expr}) + 18*sin(2*PI*(t-{start_time})/1.4)"

        return x_expr, y_expr

    @staticmethod
    def resolve_static_position(position: Any, base_w: int = 1920, base_h: int = 1080) -> Tuple[str, str]:
        """
        '["center", "bottom"]', '["right", "top"]' veya piksel koordinatlarını FFmpeg overlay parametrelerine dönüştürür.
        """
        if isinstance(position, list) and len(position) >= 2:
            h_pos, v_pos = str(position[0]).lower(), str(position[1]).lower()
        else:
            h_pos, v_pos = "center", "center"

        # Yatay (X) hesaplama
        if h_pos in ["left", "sol"]:
            x_expr = "40"
        elif h_pos in ["right", "sag", "sağ"]:
            x_expr = "main_w-overlay_w-40"
        else:
            x_expr = "(main_w-overlay_w)/2"

        # Dikey (Y) hesaplama
        if v_pos in ["top", "ust", "üst"]:
            y_expr = "40"
        elif v_pos in ["bottom", "alt"]:
            y_expr = "main_h-overlay_h-60"
        else:
            y_expr = "(main_h-overlay_h)/2"

        return x_expr, y_expr
