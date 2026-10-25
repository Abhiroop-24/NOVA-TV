"""
NOVA TV — Rendering primitives.

Omarchy-inspired monochrome drawing layer.
Sharp corners, white-on-black or black-on-white, no gradients, no glow.
Focus = filled white rectangle with black text.
"""

from __future__ import annotations

from typing import Optional, Tuple, List

import pygame

from nova import theme
from nova.assets import get_font, make_placeholder


# ── Surface helpers ───────────────────────────────────────────────────────────

def rgba_surface(w: int, h: int, color: Tuple) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill(color)
    return surf


# ── Rectangle (sharp — no border radius in mono theme) ───────────────────────

def draw_rect(
    surface: pygame.Surface,
    rect: Tuple[int, int, int, int],
    color: Tuple,
    border: int = 0,
    border_color: Tuple = (255, 255, 255),
    radius: int = 0,
) -> None:
    x, y, w, h = rect
    if len(color) == 4 and color[3] < 255:
        temp = pygame.Surface((w, h), pygame.SRCALPHA)
        temp.fill(color)
        surface.blit(temp, (x, y))
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, border_color, rect, border, border_radius=radius)


# Keep this alias for backward compat with screens that call draw_rounded_rect
def draw_rounded_rect(
    surface: pygame.Surface,
    rect: Tuple[int, int, int, int],
    color: Tuple,
    radius: int = 0,
    border: int = 0,
    border_color: Tuple = (255, 255, 255),
) -> None:
    draw_rect(surface, rect, color, border, border_color, radius=0)


# ── Text ─────────────────────────────────────────────────────────────────────

def draw_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    color: Tuple = theme.TEXT_PRIMARY,
    size: int = theme.FONT_SIZE_BODY,
    bold: bool = False,
    max_width: int = 0,
    align: str = "left",
) -> Tuple[int, int]:
    font = get_font(size, bold)
    if max_width > 0 and font.size(text)[0] > max_width:
        while len(text) > 1 and font.size(text + "...")[0] > max_width:
            text = text[:-1]
        text += "..."

    rendered = font.render(text, True, color)
    rw, rh = rendered.get_size()

    if align == "center":
        x = x - rw // 2
    elif align == "right":
        x = x - rw

    surface.blit(rendered, (x, y))
    return (rw, rh)


def draw_text_wrapped(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    max_width: int,
    max_lines: int = 3,
    color: Tuple = theme.TEXT_SECONDARY,
    size: int = theme.FONT_SIZE_BODY,
    line_spacing: int = 6,
) -> int:
    font = get_font(size)
    words = text.split()
    lines: List[str] = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    total_h = 0
    for i, line in enumerate(lines[:max_lines]):
        if i == max_lines - 1 and len(lines) > max_lines:
            line = line.rstrip() + "..."
        rendered = font.render(line, True, color)
        surface.blit(rendered, (x, y + total_h))
        total_h += rendered.get_height() + line_spacing

    return total_h


# ── Focus indicator — omarchy style: solid white border ──────────────────────

def draw_focus_ring(
    surface: pygame.Surface,
    rect: Tuple[int, int, int, int],
    radius: int = 0,
    pulse_t: float = 0.0,
) -> None:
    x, y, w, h = rect
    pad = theme.FOCUS_PADDING
    # Sharp white border, 2px — no glow, no blur
    pygame.draw.rect(
        surface,
        theme.FOCUS_BORDER,
        (x - pad, y - pad, w + pad * 2, h + pad * 2),
        theme.FOCUS_BORDER_W,
    )


def draw_focus_fill(
    surface: pygame.Surface,
    rect: Tuple[int, int, int, int],
) -> None:
    """Full white fill with black text — for nav bar items and list selections."""
    pygame.draw.rect(surface, theme.HIGHLIGHT_BG, rect)


# ── Card — sharp, minimal ────────────────────────────────────────────────────

def draw_card(
    surface: pygame.Surface,
    rect: Tuple[int, int, int, int],
    image: Optional[pygame.Surface] = None,
    label: str = "",
    sublabel: str = "",
    focused: bool = False,
    pulse_t: float = 0.0,
    badge: str = "",
) -> None:
    x, y, w, h = rect

    if focused:
        # White fill, black text
        pygame.draw.rect(surface, theme.BG_ELEVATED, rect)
        pygame.draw.rect(surface, theme.TEXT_PRIMARY, rect, 1)
    else:
        pygame.draw.rect(surface, theme.BG_CARD, rect)

    img_h = h - 64 if label else h
    if image:
        scaled = pygame.transform.smoothscale(image, (w, img_h))
        surface.blit(scaled, (x, y))
    else:
        ph = make_placeholder(w, img_h, theme.BG_ELEVATED, "")
        surface.blit(ph, (x, y))
        # Cross-hatch placeholder pattern
        pygame.draw.line(surface, theme.DIVIDER, (x, y), (x + w, y + img_h), 1)
        pygame.draw.line(surface, theme.DIVIDER, (x + w, y), (x, y + img_h), 1)

    text_color = theme.TEXT_PRIMARY
    sub_color  = theme.TEXT_SECONDARY

    if label:
        draw_text(surface, label, x + 8, y + img_h + 8,
                  text_color, theme.FONT_SIZE_CAPTION, max_width=w - 16)
    if sublabel:
        draw_text(surface, sublabel, x + 8, y + img_h + 30,
                  sub_color, theme.FONT_SIZE_SMALL, max_width=w - 16)

    if focused:
        draw_focus_ring(surface, rect)


# ── Wide card — for lists / apps ──────────────────────────────────────────────

def draw_wide_card(
    surface: pygame.Surface,
    rect: Tuple[int, int, int, int],
    icon: Optional[pygame.Surface] = None,
    label: str = "",
    sublabel: str = "",
    focused: bool = False,
    pulse_t: float = 0.0,
    status_color: Tuple = theme.STATUS_UNKNOWN,
) -> None:
    x, y, w, h = rect

    if focused:
        pygame.draw.rect(surface, theme.HIGHLIGHT_BG, rect)
        lbl_color  = theme.TEXT_INVERSE
        sub_color  = (60, 60, 60)
    else:
        pygame.draw.rect(surface, theme.BG_SURFACE, rect)
        lbl_color  = theme.TEXT_PRIMARY
        sub_color  = theme.TEXT_SECONDARY

    # Left border line (status colour)
    pygame.draw.rect(surface, status_color, (x, y, 3, h))

    icon_size = h - 20
    tx = x + 20
    if icon:
        scaled = pygame.transform.smoothscale(icon, (icon_size, icon_size))
        surface.blit(scaled, (x + 12, y + 10))
        tx = x + 12 + icon_size + 12

    draw_text(surface, label, tx, y + h // 2 - 14,
              lbl_color, theme.FONT_SIZE_BODY, bold=True,
              max_width=w - tx + x - 20)
    if sublabel:
        draw_text(surface, sublabel, tx, y + h // 2 + 6,
                  sub_color, theme.FONT_SIZE_SMALL,
                  max_width=w - tx + x - 20)

    if focused:
        draw_focus_ring(surface, rect)


# ── Nav bar item ─────────────────────────────────────────────────────────────

def draw_nav_item(
    surface: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    focused: bool = False,
    active: bool = False,
) -> None:
    """Draw a nav item. Focused = white fill. Active = underline."""
    if focused:
        pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (x, y, w, h))
        color = theme.TEXT_INVERSE
    elif active:
        color = theme.TEXT_PRIMARY
    else:
        color = theme.TEXT_SECONDARY

    font = get_font(theme.FONT_SIZE_BODY, bold=(active or focused))
    rendered = font.render(label, True, color)
    tx = x + (w - rendered.get_width()) // 2
    ty = y + (h - rendered.get_height()) // 2
    surface.blit(rendered, (tx, ty))

    if active and not focused:
        pygame.draw.line(surface, theme.TEXT_PRIMARY,
                         (x + 8, y + h - 3), (x + w - 8, y + h - 3), 2)


# ── Status bar ───────────────────────────────────────────────────────────────

def draw_status_bar(
    surface: pygame.Surface,
    y: int,
    time_str: str,
    network_connected: bool,
    ip_address: str = "",
) -> None:
    w = theme.SCREEN_W
    pygame.draw.rect(surface, theme.BG_DEEP, (0, y, w, theme.STATUS_BAR_H))
    pygame.draw.line(surface, theme.DIVIDER, (0, y), (w, y), 1)

    dot = theme.STATUS_OK if network_connected else theme.STATUS_ERROR
    pygame.draw.circle(surface, dot,
                       (theme.SAFE_MARGIN_X + 7, y + theme.STATUS_BAR_H // 2), 4)
    label = ip_address if (ip_address and network_connected) else \
            ("Online" if network_connected else "Offline")
    draw_text(surface, label, theme.SAFE_MARGIN_X + 18,
              y + theme.STATUS_BAR_H // 2 - 7,
              theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL)

    draw_text(surface, time_str,
              w - theme.SAFE_MARGIN_X,
              y + theme.STATUS_BAR_H // 2 - 7,
              theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL, align="right")


# ── Divider ───────────────────────────────────────────────────────────────────

def draw_divider(surface: pygame.Surface, y: int, margin: int = 0) -> None:
    mx = margin or theme.SAFE_MARGIN_X
    pygame.draw.line(surface, theme.DIVIDER,
                     (mx, y), (theme.SCREEN_W - mx, y), 1)


# ── Gradient (keep for compat — draws a flat overlay in mono theme) ───────────

def get_gradient_surface(w: int, h: int,
                         top_alpha: int = 0,
                         bottom_alpha: int = 200) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for row in range(h):
        t = row / max(h - 1, 1)
        a = int(top_alpha + (bottom_alpha - top_alpha) * t)
        pygame.draw.line(surf, (0, 0, 0, a), (0, row), (w, row))
    return surf


# ── Section label ─────────────────────────────────────────────────────────────

def draw_section_label(surface: pygame.Surface, x: int, y: int,
                        label: str) -> None:
    draw_text(surface, label.upper(), x, y,
              theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL, bold=True)
    pygame.draw.line(surface, theme.DIVIDER,
                     (x, y + 20), (theme.SCREEN_W - theme.SAFE_MARGIN_X, y + 20), 1)


# ── Message box ──────────────────────────────────────────────────────────────

def draw_message_box(
    surface: pygame.Surface,
    title: str,
    message: str,
    button_label: str = "OK",
    button_focused: bool = True,
    pulse_t: float = 0.0,
) -> Tuple[int, int, int, int]:
    box_w, box_h = 640, 280
    bx = (theme.SCREEN_W - box_w) // 2
    by = (theme.SCREEN_H - box_h) // 2

    # Dim
    dim = rgba_surface(theme.SCREEN_W, theme.SCREEN_H, (0, 0, 0, 180))
    surface.blit(dim, (0, 0))

    # Box — white border, black fill
    pygame.draw.rect(surface, theme.BG_DEEP, (bx, by, box_w, box_h))
    pygame.draw.rect(surface, theme.TEXT_PRIMARY, (bx, by, box_w, box_h), 1)

    draw_text(surface, title, bx + 28, by + 28,
              theme.TEXT_PRIMARY, theme.FONT_SIZE_HEADING, bold=True)
    draw_text_wrapped(surface, message, bx + 28, by + 72,
                      box_w - 56, max_lines=4,
                      color=theme.TEXT_SECONDARY, size=theme.FONT_SIZE_BODY)

    btn_w, btn_h = 120, 40
    btn_x = bx + (box_w - btn_w) // 2
    btn_y = by + box_h - btn_h - 24

    if button_focused:
        pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (btn_x, btn_y, btn_w, btn_h))
        draw_text(surface, button_label,
                  btn_x + btn_w // 2, btn_y + 10,
                  theme.TEXT_INVERSE, theme.FONT_SIZE_BODY, align="center")
    else:
        pygame.draw.rect(surface, theme.BG_ELEVATED, (btn_x, btn_y, btn_w, btn_h))
        pygame.draw.rect(surface, theme.TEXT_PRIMARY, (btn_x, btn_y, btn_w, btn_h), 1)
        draw_text(surface, button_label,
                  btn_x + btn_w // 2, btn_y + 10,
                  theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY, align="center")

    return (btn_x, btn_y, btn_w, btn_h)


# ── Spinner (loading indicator) ───────────────────────────────────────────────

def draw_spinner(surface: pygame.Surface, cx: int, cy: int,
                 t: float, radius: int = 16) -> None:
    """Simple rotating arc spinner."""
    import math
    for i in range(8):
        angle = t * 6 + i * math.pi / 4
        ax = cx + int(radius * math.cos(angle))
        ay = cy + int(radius * math.sin(angle))
        alpha = int(255 * (i + 1) / 8)
        pygame.draw.circle(surface, (alpha, alpha, alpha), (ax, ay), 3)
