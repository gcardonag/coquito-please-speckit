/**
 * 007 T017: Unit tests for the revealDetail helper shared by the chef list/detail pages.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { revealDetail } from '../../components/reveal-detail';

/** Stub window.matchMedia so every query reports `matches`. */
function stubMatchMedia(matches: boolean): void {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({ matches, media: query }) as MediaQueryList)
  );
}

/** A detail element whose scrollIntoView is a spy (jsdom does not implement it). */
function makeDetail(): { el: HTMLElement; scrollIntoView: ReturnType<typeof vi.fn> } {
  const el = document.createElement('div');
  const scrollIntoView = vi.fn();
  el.scrollIntoView = scrollIntoView;
  return { el, scrollIntoView };
}

describe('revealDetail', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('scrolls the detail panel to the top below the desktop breakpoint', () => {
    stubMatchMedia(false);
    const detail = makeDetail();

    revealDetail(detail.el);

    expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 64em)');
    expect(detail.scrollIntoView).toHaveBeenCalledWith({ block: 'start' });
  });

  it('does not scroll at desktop width, where the panel is beside the list', () => {
    stubMatchMedia(true);
    const detail = makeDetail();

    revealDetail(detail.el);

    expect(detail.scrollIntoView).not.toHaveBeenCalled();
  });

  it('is a no-op when the detail panel is missing', () => {
    stubMatchMedia(false);

    expect(() => revealDetail(null)).not.toThrow();
    expect(window.matchMedia).not.toHaveBeenCalled();
  });

  it('is a no-op when matchMedia is unavailable', () => {
    vi.stubGlobal('matchMedia', undefined);
    const detail = makeDetail();

    expect(() => revealDetail(detail.el)).not.toThrow();
    expect(detail.scrollIntoView).not.toHaveBeenCalled();
  });
});
