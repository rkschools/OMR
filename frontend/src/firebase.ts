import { initializeApp } from 'firebase/app';
import { getAuth, connectAuthEmulator } from 'firebase/auth';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';

const firebaseConfig = {
  projectId: "rise-omr-backend-2027",
  appId: "1:104405722836:web:de47e9c2acc466272ffd41",
  apiKey: "AIzaSyDwEDw9jcYTGSUL-MCJ53UGlPoOLUtr1x8",
  authDomain: "rise-omr-backend-2027.firebaseapp.com",
  messagingSenderId: "104405722836"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

try {
  connectFirestoreEmulator(db, '127.0.0.1', 8080);
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true });
} catch (e) {
  // Already connected
}
