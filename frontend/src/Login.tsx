import React, { useState, useEffect } from 'react';
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';
import { doc, getDoc, writeBatch } from 'firebase/firestore';
import { auth, db } from './firebase';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [ruleError] = useState(false);
  const [isSetupMode, setIsSetupMode] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { currentUser } = useAuth();

  useEffect(() => {
    if (currentUser) {
      navigate('/');
    }
  }, [currentUser, navigate]);

  useEffect(() => {
    const checkSetup = async () => {
      try {
        const setupDoc = await getDoc(doc(db, 'system', 'setup'));
        if (!setupDoc.exists() || !setupDoc.data().isSetup) {
          setIsSetupMode(true);
        } else {
          setIsSetupMode(false);
        }
      } catch (err: any) {
        console.error("Failed to fetch setup status:", err);
        setIsSetupMode(true);
      } finally {
        setLoading(false);
      }
    };
    checkSetup();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    try {
      if (isSetupMode) {
        // 1. Create or Login User in Firebase Auth
        let user;
        try {
            const userCred = await createUserWithEmailAndPassword(auth, email, password);
            user = userCred.user;
        } catch (createErr: any) {
            if (createErr.code === 'auth/email-already-in-use') {
                // If they already created the account but setup failed halfway, log them in
                const loginCred = await signInWithEmailAndPassword(auth, email, password);
                user = loginCred.user;
            } else {
                throw createErr;
            }
        }
        
        // 2. Perform Atomic Batched Write
        const batch = writeBatch(db);
        
        // Write users/{uid} document with role = admin
        batch.set(doc(db, 'users', user.uid), {
          email: user.email,
          role: 'admin',
          createdAt: new Date()
        });

        // Mark system as setup
        batch.set(doc(db, 'system', 'setup'), {
          isSetup: true,
          setupAt: new Date(),
          setupBy: user.uid
        });
        
        await batch.commit();

        navigate('/');
      } else {
        // Normal Login
        await signInWithEmailAndPassword(auth, email, password);
        navigate('/');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center' }}>Loading...</div>;
  }

  return (
    <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', backgroundColor: 'var(--bg-main)' }}>
      <div className="card" style={{ width: '100%', maxWidth: '400px' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '0.5rem', color: 'var(--primary-color)' }}>
          {isSetupMode ? 'Create Administrator Account' : 'RISE OMR Platform'}
        </h2>
        
        {isSetupMode && !ruleError && (
          <p style={{ textAlign: 'center', marginBottom: '1.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            No users found. Please create the initial admin account.
          </p>
        )}
        {ruleError && (
          <div style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
            <strong>Firebase Rules Error:</strong> You haven't updated your Firebase Console rules yet. <br/><br/>
            Go to Firebase Console &rarr; Firestore Database &rarr; Rules, paste the contents of <code>firestore.rules</code>, and click <strong>Publish</strong>.
          </div>
        )}
        {!isSetupMode && (
          <p style={{ textAlign: 'center', marginBottom: '1.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Sign in to continue.
          </p>
        )}

        {error && <div style={{ color: 'red', marginBottom: '1rem', fontSize: '0.875rem', padding: '0.5rem', backgroundColor: '#fee2e2', borderRadius: '4px' }}>{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input 
              type="email" 
              className="form-control" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required 
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input 
              type="password" 
              className="form-control" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
              minLength={6}
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
            {isSetupMode ? 'Create Account & Login' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
