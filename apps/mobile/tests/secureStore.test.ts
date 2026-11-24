import { setSecureItem, getSecureItem, deleteSecureItem } from '../src/utils/secureStore';

describe('NEXUS Mobile SecureStore Platform Wrapper', () => {
  test('writes, reads, and deletes securely with fallback', async () => {
    await setSecureItem('test_key', 'sovereign_secret_payload');
    const val = await getSecureItem('test_key');
    expect(val).toBe('sovereign_secret_payload');

    await deleteSecureItem('test_key');
    const after = await getSecureItem('test_key');
    expect(after).toBeNull();
  });
});
