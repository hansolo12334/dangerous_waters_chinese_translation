#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <unknwn.h>
#include <cstdio>
#include <cstring>
#include <cwchar>

#include "generated_glyph_map.h"

namespace {

constexpr DWORD kMeasureAddress = 0x0047E850;
constexpr DWORD kLineRenderAddress = 0x0047EAC0;
constexpr DWORD kTextRenderAddress = 0x0047EBA0;
constexpr DWORD kDrawGlyphAddress = 0x0047EDF0;
constexpr DWORD kFontConstructorAddress = 0x0047E510;
constexpr DWORD kSetFontColorAddress = 0x0047E9D0;
constexpr DWORD kOperatorNewAddress = 0x0045BFC8;
constexpr DWORD kFinalizeSharedFontsThunkAddress = 0x00401582;
constexpr DWORD kFinalizeSharedFontsOriginalAddress = 0x0042DC00;
constexpr DWORD kSharedPathAddress = 0x00815E00;

using DirectInput8CreateFunction = HRESULT(WINAPI *)(HINSTANCE, DWORD, REFIID, LPVOID *, IUnknown *);
using AllocateFunction = void *(__cdecl *)(unsigned int);
using FontConstructorFunction = void *(__thiscall *)(void *, const char *, int);
using SetColorFunction = int(__thiscall *)(void *, unsigned short);
using DrawGlyphFunction = void(__thiscall *)(void *, int, int, int, int, int, int, int);
using FinalizeSharedFontsFunction = int(__cdecl *)();
using MeasureFunction = void(__thiscall *)(void *, const unsigned char *, int, int *, unsigned char);
using LineRenderFunction = int(__thiscall *)(void *, int, int, int, const unsigned char *, int);
using TextRenderFunction = void(__thiscall *)(void *, int, const unsigned char *, int, int *, unsigned char);

HMODULE gRealDinput8;
DirectInput8CreateFunction gDirectInput8Create;
MeasureFunction gOriginalMeasure;
LineRenderFunction gOriginalLineRender;
TextRenderFunction gOriginalTextRender;
void *gChineseFonts[64];

int ReadInt(const void *object, int offset) {
    return *reinterpret_cast<const int *>(reinterpret_cast<const unsigned char *>(object) + offset);
}

void WriteWord(void *object, int offset, unsigned short value) {
    *reinterpret_cast<unsigned short *>(reinterpret_cast<unsigned char *>(object) + offset) = value;
}

bool ContainsUtf8(const unsigned char *text, int length) {
    if (!text) return false;
    if (length < 0) length = static_cast<int>(std::strlen(reinterpret_cast<const char *>(text)));
    for (int index = 0; index < length; ++index) {
        if (text[index] >= 0x80) return true;
    }
    return false;
}

unsigned int DecodeUtf8(const unsigned char *text, int remaining, int *consumed) {
    unsigned char first = text[0];
    *consumed = 1;
    if (first < 0x80 || remaining < 2) return first;
    if ((first & 0xE0) == 0xC0 && (text[1] & 0xC0) == 0x80) {
        *consumed = 2;
        return ((first & 0x1F) << 6) | (text[1] & 0x3F);
    }
    if (remaining >= 3 && (first & 0xF0) == 0xE0
        && (text[1] & 0xC0) == 0x80 && (text[2] & 0xC0) == 0x80) {
        *consumed = 3;
        return ((first & 0x0F) << 12) | ((text[1] & 0x3F) << 6) | (text[2] & 0x3F);
    }
    if (remaining >= 4 && (first & 0xF8) == 0xF0
        && (text[1] & 0xC0) == 0x80 && (text[2] & 0xC0) == 0x80
        && (text[3] & 0xC0) == 0x80) {
        *consumed = 4;
        return ((first & 0x07) << 18) | ((text[1] & 0x3F) << 12)
            | ((text[2] & 0x3F) << 6) | (text[3] & 0x3F);
    }
    return '?';
}

const UnicodeGlyph *FindChineseGlyph(unsigned int codepoint) {
    for (unsigned int index = 0; index < kUnicodeGlyphCount; ++index) {
        if (kUnicodeGlyphs[index].codepoint == codepoint) return &kUnicodeGlyphs[index];
    }
    return nullptr;
}

void *LoadChineseFont(unsigned int page) {
    if (page >= kUnicodeFontPageCount || page >= 64) return nullptr;
    if (gChineseFonts[page]) return gChineseFonts[page];
    const char *sharedPath = reinterpret_cast<const char *>(kSharedPathAddress);
    if (!sharedPath || !sharedPath[0]) return nullptr;
    char fontPath[MAX_PATH];
    std::sprintf(fontPath, "%s\\dw_zh_%02u.bmp", sharedPath, page);
    auto allocate = reinterpret_cast<AllocateFunction>(kOperatorNewAddress);
    auto constructor = reinterpret_cast<FontConstructorFunction>(kFontConstructorAddress);
    auto setColor = reinterpret_cast<SetColorFunction>(kSetFontColorAddress);
    void *font = allocate(0xB0);
    if (font) font = constructor(font, fontPath, 1);
    if (!font || !ReadInt(font, 96)) return nullptr;
    setColor(font, 0xFF);
    gChineseFonts[page] = font;
    return font;
}

int __cdecl HookFinalizeSharedFonts() {
    for (unsigned int page = 0; page < kUnicodeFontPageCount; ++page) LoadChineseFont(page);
    return reinterpret_cast<FinalizeSharedFontsFunction>(kFinalizeSharedFontsOriginalAddress)();
}

struct ResolvedGlyph {
    void *font;
    unsigned char slot;
    int consumed;
    bool draw;
};

int GlyphHeight(void *font, unsigned char slot);

bool ShouldDrawCjkLayer(void *sourceFont) {
    if (!kSkipCjkOutlineLayers) return true;
    if (!sourceFont || !ReadInt(sourceFont, 88)) return true;
    return GlyphHeight(sourceFont, static_cast<unsigned char>('A')) <= kMaxCjkSourceHeight;
}

ResolvedGlyph ResolveGlyph(void *sourceFont, const unsigned char *text, int remaining) {
    int consumed = 1;
    unsigned int codepoint = DecodeUtf8(text, remaining, &consumed);
    if (codepoint < 0x80) {
        return {sourceFont, static_cast<unsigned char>(codepoint), consumed, true};
    }
    const UnicodeGlyph *mapped = FindChineseGlyph(codepoint);
    if (mapped) {
        void *font = LoadChineseFont(mapped->page);
        if (font) {
            WriteWord(font, 76, *reinterpret_cast<unsigned short *>(
                reinterpret_cast<unsigned char *>(sourceFont) + 76));
            return {font, mapped->slot, consumed, ShouldDrawCjkLayer(sourceFont)};
        }
    }
    return {sourceFont, static_cast<unsigned char>('?'), consumed, true};
}

int GlyphWidth(void *font, unsigned char slot) {
    int records = ReadInt(font, 88);
    return ReadInt(reinterpret_cast<void *>(records + slot * 20), 12);
}

int GlyphHeight(void *font, unsigned char slot) {
    int records = ReadInt(font, 88);
    return ReadInt(reinterpret_cast<void *>(records + slot * 20), 16);
}

void DrawResolvedGlyph(void *sourceFont, int destination, int x, int y, const ResolvedGlyph &glyph) {
    int records = ReadInt(glyph.font, 88);
    int record = records + glyph.slot * 20;
    auto draw = reinterpret_cast<DrawGlyphFunction>(kDrawGlyphAddress);
    draw(
        glyph.font,
        destination,
        x,
        y,
        ReadInt(glyph.font, 60) + ReadInt(reinterpret_cast<void *>(record), 4),
        ReadInt(glyph.font, 64) + ReadInt(reinterpret_cast<void *>(record), 8),
        ReadInt(reinterpret_cast<void *>(record), 12),
        ReadInt(reinterpret_cast<void *>(record), 16));
}

void MeasureUtf8(void *font, const unsigned char *text, int length, int *dimensions, unsigned char flags) {
    dimensions[0] = 0;
    dimensions[1] = 0;
    if (!text || !ReadInt(font, 96) || !ReadInt(font, 88)) return;
    if (length < 0) length = static_cast<int>(std::strlen(reinterpret_cast<const char *>(text)));
    int lineWidth = 0;
    int defaultHeight = GlyphHeight(font, static_cast<unsigned char>(' '));
    int lineHeight = defaultHeight;
    for (int offset = 0; offset < length;) {
        unsigned char current = text[offset];
        if (!(flags & 0x10) && current == '\n') {
            if (lineWidth > dimensions[0]) dimensions[0] = lineWidth;
            dimensions[1] += lineHeight;
            lineWidth = 0;
            lineHeight = defaultHeight;
            ++offset;
            continue;
        }
        if (current == '\t') {
            lineWidth = 30 * ((lineWidth + 30) / 30);
            ++offset;
            continue;
        }
        if (current && current <= 7) {
            lineWidth = ReadInt(font, 104 + current * 4);
            ++offset;
            continue;
        }
        ResolvedGlyph glyph = ResolveGlyph(font, text + offset, length - offset);
        lineWidth += ReadInt(glyph.font, 68) + GlyphWidth(glyph.font, glyph.slot);
        int height = GlyphHeight(glyph.font, glyph.slot);
        if (height > lineHeight) lineHeight = height;
        offset += glyph.consumed;
    }
    if (lineWidth > dimensions[0]) dimensions[0] = lineWidth;
    dimensions[1] += lineHeight;
}

void __fastcall HookMeasure(
    void *font, void *, const unsigned char *text, int length, int *dimensions, unsigned char flags) {
    if (!ContainsUtf8(text, length)) {
        gOriginalMeasure(font, text, length, dimensions, flags);
        return;
    }
    if (dimensions) MeasureUtf8(font, text, length, dimensions, flags);
}

int __fastcall HookLineRender(
    void *font, void *, int destination, int x, int y, const unsigned char *text, int length) {
    if (!ContainsUtf8(text, length)) return gOriginalLineRender(font, destination, x, y, text, length);
    if (!ReadInt(font, 96)) return length;
    int lineStartX = x;
    for (int offset = 0; offset < length;) {
        unsigned char current = text[offset];
        if (current == '\t') {
            x = 30 * ((x + 30) / 30);
            ++offset;
            continue;
        }
        if (current && current <= 7) {
            x = lineStartX + ReadInt(font, 104 + current * 4);
            ++offset;
            continue;
        }
        ResolvedGlyph glyph = ResolveGlyph(font, text + offset, length - offset);
        if (glyph.draw) DrawResolvedGlyph(font, destination, x, y, glyph);
        x += ReadInt(glyph.font, 68) + GlyphWidth(glyph.font, glyph.slot);
        offset += glyph.consumed;
    }
    return length;
}

void SetupTextDestination(void *font, int sourceDestination, int *rect, unsigned char flags, int *destination) {
    *destination = sourceDestination;
    if (flags & 0x40) return;
    void *graphics = *reinterpret_cast<void **>(reinterpret_cast<unsigned char *>(font) + 164);
    void **vtable = *reinterpret_cast<void ***>(graphics);
    using SetupFunction = void(__thiscall *)(void *, int, int, int, int, int, int);
    reinterpret_cast<SetupFunction>(vtable[11])(
        graphics, sourceDestination, ReadInt(font, 160), rect[0], rect[1],
        rect[2] - rect[0] + 1, rect[3] - rect[1] + 1);
    *destination = ReadInt(font, 160);
}

void __fastcall HookTextRender(
    void *font, void *, int destination, const unsigned char *text, int length, int *rect, unsigned char flags) {
    if (!ContainsUtf8(text, length)) {
        gOriginalTextRender(font, destination, text, length, rect, flags);
        return;
    }
    if (!text || !destination || !rect || !ReadInt(font, 88) || !ReadInt(font, 96)) return;
    if (length < 0) length = static_cast<int>(std::strlen(reinterpret_cast<const char *>(text)));
    if (length <= 0) return;
    int drawDestination;
    SetupTextDestination(font, destination, rect, flags, &drawDestination);
    int vertical = flags & 0x0C;
    int horizontal = flags & 0x03;
    int y = rect[1];
    if (vertical) {
        int fullSize[2];
        MeasureUtf8(font, text, length, fullSize, flags);
        if (vertical == 8) y = rect[3] - fullSize[1] + 1;
        else if (vertical == 4) y = rect[1] + (rect[3] - rect[1] - fullSize[1] + 1) / 2;
    }
    for (int lineStart = 0; lineStart < length;) {
        int lineLength = (flags & 0x10) ? length - lineStart : 0;
        if (!(flags & 0x10)) {
            while (lineStart + lineLength < length && text[lineStart + lineLength] != '\n') ++lineLength;
        }
        int lineSize[2];
        MeasureUtf8(font, text + lineStart, lineLength, lineSize, flags);
        int x = rect[0];
        if (horizontal == 2) x = rect[2] - lineSize[0] + 1;
        else if (horizontal == 1) x = rect[0] + (rect[2] - rect[0] - lineSize[0] + 1) / 2;
        HookLineRender(font, nullptr, drawDestination, x, y, text + lineStart, lineLength);
        y += lineSize[1];
        lineStart += lineLength;
        if (lineStart < length && text[lineStart] == '\n') ++lineStart;
    }
}

void *InstallJump(DWORD address, void *replacement, unsigned int stolenLength) {
    unsigned char *source = reinterpret_cast<unsigned char *>(address);
    unsigned char *trampoline = reinterpret_cast<unsigned char *>(
        VirtualAlloc(nullptr, stolenLength + 5, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!trampoline) return nullptr;
    std::memcpy(trampoline, source, stolenLength);
    trampoline[stolenLength] = 0xE9;
    *reinterpret_cast<int *>(trampoline + stolenLength + 1) =
        source + stolenLength - (trampoline + stolenLength + 5);
    DWORD originalProtection;
    VirtualProtect(source, stolenLength, PAGE_EXECUTE_READWRITE, &originalProtection);
    source[0] = 0xE9;
    *reinterpret_cast<int *>(source + 1) =
        reinterpret_cast<unsigned char *>(replacement) - (source + 5);
    for (unsigned int index = 5; index < stolenLength; ++index) source[index] = 0x90;
    VirtualProtect(source, stolenLength, originalProtection, &originalProtection);
    FlushInstructionCache(GetCurrentProcess(), source, stolenLength);
    return trampoline;
}

bool InstallDirectJump(DWORD address, void *replacement) {
    unsigned char *source = reinterpret_cast<unsigned char *>(address);
    DWORD originalProtection;
    if (!VirtualProtect(source, 5, PAGE_EXECUTE_READWRITE, &originalProtection)) return false;
    source[0] = 0xE9;
    *reinterpret_cast<int *>(source + 1) =
        reinterpret_cast<unsigned char *>(replacement) - (source + 5);
    VirtualProtect(source, 5, originalProtection, &originalProtection);
    FlushInstructionCache(GetCurrentProcess(), source, 5);
    return true;
}

bool InstallFuiHooks() {
    if (!InstallDirectJump(
            kFinalizeSharedFontsThunkAddress, reinterpret_cast<void *>(&HookFinalizeSharedFonts))) {
        return false;
    }
    gOriginalMeasure = reinterpret_cast<MeasureFunction>(
        InstallJump(kMeasureAddress, reinterpret_cast<void *>(&HookMeasure), 6));
    gOriginalLineRender = reinterpret_cast<LineRenderFunction>(
        InstallJump(kLineRenderAddress, reinterpret_cast<void *>(&HookLineRender), 6));
    gOriginalTextRender = reinterpret_cast<TextRenderFunction>(
        InstallJump(kTextRenderAddress, reinterpret_cast<void *>(&HookTextRender), 8));
    return gOriginalMeasure && gOriginalLineRender && gOriginalTextRender;
}

bool LoadRealDinput8() {
    wchar_t systemDirectory[MAX_PATH];
    if (!GetSystemDirectoryW(systemDirectory, MAX_PATH)) return false;
    std::wcscat(systemDirectory, L"\\dinput8.dll");
    gRealDinput8 = LoadLibraryW(systemDirectory);
    if (!gRealDinput8) return false;
    gDirectInput8Create = reinterpret_cast<DirectInput8CreateFunction>(
        GetProcAddress(gRealDinput8, "DirectInput8Create"));
    return gDirectInput8Create != nullptr;
}

}

extern "C" HRESULT WINAPI DirectInput8Create(
    HINSTANCE instance, DWORD version, REFIID iid, LPVOID *result, IUnknown *outer) {
    if (!gDirectInput8Create && !LoadRealDinput8()) return E_FAIL;
    return gDirectInput8Create(instance, version, iid, result, outer);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(instance);
        LoadRealDinput8();
        InstallFuiHooks();
    }
    return TRUE;
}
