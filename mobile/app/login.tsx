import React, { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { Theme } from '../constants/Colors';
import { errorText } from '../services/api';


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
        <TextInput style={s.input} placeholder="Username" placeholderTextColor={Theme.whiteMuted} autoCapitalize="none" autoCorrect={false} value={username} onChangeText={setUsername} />
        <TextInput style={s.input} placeholder="Password" placeholderTextColor={Theme.whiteMuted} secureTextEntry value={password} onChangeText={setPassword} onSubmitEditing={submit} />
        {error ? <Text style={s.error}>{error}</Text> : null}
        <Pressable style={[s.button, busy && { opacity: 0.6 }]} onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color={Theme.white} /> : <Text style={s.buttonText}>Sign in</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: Theme.page, justifyContent: 'center', padding: 24 },
  box: { gap: 12 },
  logo: { color: Theme.white, fontSize: 36, fontWeight: '800' },
  sub: { color: Theme.whiteMuted, marginBottom: 16 },
  input: { backgroundColor: Theme.chip, color: Theme.white, borderRadius: 16, padding: 16, fontSize: 16 },
  error: { color: '#FCA5A5' },
  button: { backgroundColor: Theme.accent, borderRadius: 999, padding: 16, alignItems: 'center', marginTop: 4 },
  buttonText: { color: Theme.white, fontWeight: '800', fontSize: 16 },
});
