"""OtoEdit Animation Effects - Görsel ve metin kaplamaları için animasyon hesaplamaları."""
from typing import Dict, Any, Tuple


class AnimationEffects:
    """Yazı ve görsel kaplamaları için FFmpeg ve ASS uyumlu animasyon parametreleri üretir."""

    @staticmethod
    def get_ass_tags(animation_type: str, duration_sec: float, pos_x: int = 0, pos_y: int = 0) -> str:
        r"""
        ASS formatı için animasyon kontrol etiketlerini döndürür.
        Örn: fade -> \fad(300,300)
             pop-up -> \t(0, 300, \fscx100\fscy100)
             slide-left -> \move(x_start, y, x_end, y, 0, 400)
        """
        duration_ms = int(duration_sec * 1000)
        anim = (animation_type or "").lower().strip()

        if anim == "fade":
            fade_in = min(300, max(50, int(duration_ms * 0.1)))
            fade_out = min(300, max(50, int(duration_ms * 0.1)))
            return f"\\fad({fade_in},{fade_out})"

        elif anim == "pop-up":
            # 0-250ms arasında %50'den %100'e hızlı büyüme + hafif fade
            return "\\fscx50\\fscy50\\t(0,250,\\fscx100\\fscy100)\\fad(100,200)"

        elif anim == "slide-left":
            # Sağdan sola kayarak gelme
            start_x = pos_x + 300
            anim_dur = min(400, int(duration_ms * 0.2))
            return f"\\move({start_x},{pos_y},{pos_x},{pos_y},0,{anim_dur})"

        elif anim == "slide-right":
            # Soldan sağa kayarak gelme
            start_x = max(0, pos_x - 300)
            anim_dur = min(400, int(duration_ms * 0.2))
            return f"\\move({start_x},{pos_y},{pos_x},{pos_y},0,{anim_dur})"

        elif anim == "slide-up":
            # Aşağıdan yukarıya kayarak gelme
            start_y = pos_y + 200
            anim_dur = min(400, int(duration_ms * 0.2))
            return f"\\move({pos_x},{start_y},{pos_x},{pos_y},0,{anim_dur})"

        elif anim == "slide-down":
            # Yukarıdan aşağıya kayarak gelme
            start_y = max(0, pos_y - 200)
            anim_dur = min(400, int(duration_ms * 0.2))
            return f"\\move({pos_x},{start_y},{pos_x},{pos_y},0,{anim_dur})"

        return ""

    @staticmethod
    def get_ffmpeg_overlay_coords(
        position: Any,
        base_w: int = 1920,
        base_h: int = 1080,
        anim_type: str = "fade",
        start_time: float = 0.0,
        duration: float = 5.0
    ) -> Tuple[str, str]:
        """
        FFmpeg filter_complex overlay filtresi için x ve y matematiksel ifadelerini döndürür.
        Örn: slide-left -> x='if(lt(t, T0+0.5), W - (W-target_x)*(t-T0)/0.5, target_x)'
        """
        target_x, target_y = AnimationEffects.resolve_static_position(position, base_w, base_h)
        anim = (anim_type or "").lower().strip()
        end_time = start_time + duration

        if anim == "slide-left":
            anim_duration = 0.4
            # Ekranın sağından target_x konumuna doğru kayar
            x_expr = (
                f"if(lt(t, {start_time + anim_duration}), "
                f"main_w - (main_w - ({target_x})) * ((t - {start_time}) / {anim_duration}), "
                f"{target_x})"
            )
            return x_expr, target_y

        elif anim == "slide-right":
            anim_duration = 0.4
            # Ekranın solundan target_x konumuna doğru kayar
            x_expr = (
                f"if(lt(t, {start_time + anim_duration}), "
                f"-overlay_w + ({target_x} + overlay_w) * ((t - {start_time}) / {anim_duration}), "
                f"{target_x})"
            )
            return x_expr, target_y

        elif anim == "slide-up":
            anim_duration = 0.4
            y_expr = (
                f"if(lt(t, {start_time + anim_duration}), "
                f"main_h - (main_h - ({target_y})) * ((t - {start_time}) / {anim_duration}), "
                f"{target_y})"
            )
            return target_x, y_expr

        return target_x, target_y

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
