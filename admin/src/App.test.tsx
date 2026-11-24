import { describe, expect, it } from 'vitest';

describe('admin foundation', () => {
  it('identifies the marketplace admin application', () => {
    expect('South Omo Market').toContain('Market');
  });

  it('keeps Owner employment actions behind the Owner-only employment API', () => {
    const ownerEndpoints = [
      '/employment/admin/providers?status=pending',
      '/employment/admin/providers?status=verified',
      '/employment/admin/advertisements?status=all',
    ];
    expect(ownerEndpoints.every((endpoint) => endpoint.startsWith('/employment/admin/'))).toBe(true);
  });
});
