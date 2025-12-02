import { Linking } from 'react-native';

let _router: any = null;

export function setRouter(router: any) {
  _router = router;
}

export function navigate(path: string) {
  try {
    if (_router && typeof _router.push === 'function') {
      // prefer replace so back button doesn't return to protected page
      if (typeof _router.replace === 'function') {
        _router.replace(path);
      } else {
        _router.push(path);
      }
      return;
    }
  } catch {
    // fallthrough to other strategies
  }

  if (typeof window !== 'undefined' && window.location) {
    window.location.href = path;
    return;
  }

  // Last-resort: try Linking deep link
  try {
    Linking.openURL(path).catch(() => {});
  } catch {
    // ignore — nothing else we can do
  }
}
