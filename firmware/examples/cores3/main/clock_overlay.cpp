// SPDX-FileCopyrightText: 2026 karaage0703
// SPDX-License-Identifier: MIT

#include "clock_overlay.h"

#include <string.h>

namespace {
char g_clock_text[6] = "";
uint32_t g_clock_updated_ms = 0;
bool g_clock_dirty = false;
bool g_clock_last_visible = false;
}  // namespace

void clockOverlaySetTime(const char* hhmm, uint32_t now_ms) {
    memcpy(g_clock_text, hhmm, 5);
    g_clock_text[5] = '\0';
    g_clock_updated_ms = now_ms;
    g_clock_dirty = true;
}

bool clockOverlayVisibleAt(uint32_t now_ms) {
    return g_clock_text[0] != '\0' && (now_ms - g_clock_updated_ms) <= CLOCK_STALE_MS;
}

uint32_t clockOverlayAgeMs(uint32_t now_ms) {
    if (g_clock_text[0] == '\0') return 0;
    return now_ms - g_clock_updated_ms;
}

const char* clockOverlayText() {
    return g_clock_text;
}

bool clockOverlayDirty() {
    return g_clock_dirty;
}

bool clockOverlayLastVisible() {
    return g_clock_last_visible;
}

void clockOverlayMarkDirty() {
    g_clock_dirty = true;
}

void clockOverlayMarkDrawn(bool visible, uint32_t now_ms) {
    (void)now_ms;
    g_clock_last_visible = visible;
    g_clock_dirty = false;
}
