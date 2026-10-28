import assert from 'node:assert/strict';
import { test, runTests } from './harness.mjs';
import { ConfigurationError, validateVideoUrl } from '../../examples/nodejs/client.mjs';

function accepts(url, canonicalUrl, form) {
  const result = validateVideoUrl(url);
  assert.equal(result.canonicalUrl, canonicalUrl);
  assert.equal(result.form, form);
}

function rejects(url) {
  assert.throws(() => validateVideoUrl(url), ConfigurationError);
}

test('watch URL is canonicalized', () => {
  accepts(
    'https://www.facebook.com/watch/?v=1115932820735409',
    'https://www.facebook.com/watch/?v=1115932820735409',
    'watch',
  );
});

test('watch URL without www or trailing slash', () => {
  accepts('https://facebook.com/watch?v=1234567890', 'https://www.facebook.com/watch/?v=1234567890', 'watch');
});

test('tracking parameters are dropped', () => {
  accepts(
    'https://m.facebook.com/watch/?v=42&mibextid=rS40aB7S9Ucbxw6v&ref=share',
    'https://www.facebook.com/watch/?v=42',
    'watch',
  );
});

test('page video URL preserves slug case', () => {
  accepts(
    'https://web.facebook.com/SomePage.Name/videos/987654321/',
    'https://www.facebook.com/SomePage.Name/videos/987654321/',
    'page_video',
  );
});

test('videos, reel, video.php and share forms', () => {
  accepts('https://www.facebook.com/videos/1234567890', 'https://www.facebook.com/videos/1234567890/', 'video');
  accepts('https://www.facebook.com/reel/1234567890/', 'https://www.facebook.com/reel/1234567890/', 'reel');
  accepts(
    'https://www.facebook.com/reel/1234567890?mibextid=rS40aB7S9Ucbxw6v',
    'https://www.facebook.com/reel/1234567890/',
    'reel',
  );
  accepts(
    'https://www.facebook.com/video.php?v=1234567890',
    'https://www.facebook.com/video.php?v=1234567890',
    'video_php',
  );
  accepts('https://www.facebook.com/share/v/AbCdEf123/', 'https://www.facebook.com/share/v/AbCdEf123/', 'share');
  accepts('https://www.facebook.com/share/r/AbCdEf123', 'https://www.facebook.com/share/r/AbCdEf123/', 'share');
});

test('fb.watch short links', () => {
  accepts('https://fb.watch/AbCdEf123/', 'https://fb.watch/AbCdEf123/', 'short_link');
  accepts('https://www.fb.watch/AbCdEf123', 'https://fb.watch/AbCdEf123/', 'short_link');
});

test('rejects non-https and foreign hosts', () => {
  rejects('http://www.facebook.com/reel/123/');
  rejects('ftp://www.facebook.com/reel/123/');
  rejects('https://www.instagram.com/reel/abc/');
  rejects('https://facebook.com.evil.example/reel/123/');
});

test('rejects site sections and malformed watch URLs', () => {
  rejects('https://www.facebook.com/login/');
  rejects('https://www.facebook.com/groups/123/');
  rejects('https://www.facebook.com/stories/123/');
  rejects('https://www.facebook.com/watch/');
  rejects('https://www.facebook.com/watch/?v=abc');
  rejects('https://www.facebook.com/watch/?v=1&v=2');
});

test('rejects fragment, userinfo, port, whitespace and unknown forms', () => {
  rejects('https://www.facebook.com/reel/123/#comments');
  rejects('https://user:pass@www.facebook.com/reel/123/');
  rejects('https://www.facebook.com:8443/reel/123/');
  rejects(' https://www.facebook.com/reel/123/');
  rejects('https://www.facebook.com/reel/123/ ');
  rejects('');
  rejects(null);
  rejects('[video](https://www.facebook.com/reel/123/)');
  rejects('https://www.facebook.com/SomePage/videos/not-a-number');
  rejects('https://www.facebook.com/share/x/AbCdEf/');
  rejects(`https://www.facebook.com/reel/1/${'a'.repeat(2100)}`);
});

await runTests();
