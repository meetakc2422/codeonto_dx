import React, { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { Colors } from '../constants/Colors';
import { errorText } from '../services/api';

const C = Colors.dark;

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    if (!username.trim() || !password) return setError('Enter your username and password');
    setBusy(true);
    setError('');
    try {
      await login(username, password);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView style={s.page} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={s.box}>
        <Text style={s.logo}>SocialSpork</Text>
        <Text style={s.sub}>Every outlet, every platform, one dashboard.</Text>
        <TextInput style={s.input} placeholder="Username" placeholderTextColor={C.textMuted} autoCapitalize="none" autoCorrect={false} value={username} onChangeText={setUsername} />
        <TextInput style={s.input} placeholder="Password" placeholderTextColor={C.textMuted} secureTextEntry value={password} onChangeText={setPassword} onSubmitEditing={submit} />
        {error ? <Text style={s.error}>{error}</Text> : null}
        <Pressable style={[s.button, busy && { opacity: 0.6 }]} onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={s.buttonText}>Sign in</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: C.background, justifyContent: 'center', padding: 24 },
  box: { gap: 12 },
  logo: { color: C.text, fontSize: 34, fontWeight: '800' },
  sub: { color: C.textSecondary, marginBottom: 16 },
  input: { backgroundColor: C.surface, color: C.text, borderRadius: 12, padding: 14, fontSize: 16, borderWidth: 1, borderColor: C.cardBorder },
  error: { color: Colors.danger },
  button: { backgroundColor: Colors.primary, borderRadius: 12, padding: 15, alignItems: 'center', marginTop: 4 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
