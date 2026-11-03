import { initializeApp } from 'firebase/app';
import { getAuth, connectAuthEmulator } from 'firebase/auth';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';

const firebaseConfig = {
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "rise-omr-backend-2027",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "",
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "rise-omr-backend-2027.firebaseapp.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || ""
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

const useEmulator = import.meta.env.VITE_USE_FIREBASE_EMULATOR !== 'false';
if (useEmulator) {
  try {
    connectFirestoreEmulator(db, '127.0.0.1', 8080);
    connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true });
  } catch (e) {
    // Already connected
  }
}
