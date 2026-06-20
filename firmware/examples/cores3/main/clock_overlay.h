// SPDX-FileCopyrightText: 2026 karaage0703
// SPDX-License-Identifier: MIT

#pragma once

#include <M5Unified.h>
#include <stdint.h>

constexpr uint32_t CLOCK_STALE_MS = 90000;
constexpr uint32_t CLOCK_DRAW_INTERVAL_MS = 250;

void clockOverlaySetTime(const char* hhmm, uint32_t now_ms);
bool clockOverlayVisibleAt(uint32_t now_ms);
uint32_t clockOverlayAgeMs(uint32_t now_ms);
const char* clockOverlayText();
bool clockOverlayDirty();
bool clockOverlayLastVisible();
void clockOverlayMarkDirty();
void clockOverlayMarkDrawn(bool visible, uint32_t now_ms);

template <typename Gfx>
void clockOverlayClearOn(Gfx& gfx) {
    constexpr int x = 6;
    constexpr int y = 6;
    constexpr int w = 72;
    constexpr int h = 26;
    gfx.fillRoundRect(x, y, w, h, 4, TFT_BLACK);
}

template <typename Gfx>
bool clockOverlayDrawOn(Gfx& gfx, uint32_t now_ms) {
    if (!clockOverlayVisibleAt(now_ms)) return false;

    constexpr int x = 6;
    constexpr int y = 6;
    constexpr int w = 72;
    constexpr int h = 26;

    gfx.fillRoundRect(x, y, w, h, 4, TFT_BLACK);
    gfx.drawRoundRect(x, y, w, h, 4, TFT_DARKGREY);
    gfx.setTextColor(TFT_WHITE, TFT_BLACK);
    gfx.setTextSize(2);
    gfx.setTextDatum(top_left);
    gfx.drawString(String(clockOverlayText()), x + 7, y + 5);
    return true;
}
