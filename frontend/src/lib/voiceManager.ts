/**
 * Interviewer Voice & Persona Manager.
 * Ensures 100% deterministic, consistent voice synthesis without mid-interview voice changes.
 * Preloads browser voices, locks the selected voice for the session,
 * and fixes Chromium SpeechSynthesis garbage-collection and pause/resume truncation bugs.
 */

export interface InterviewerPersona {
  id: string;
  name: string;
  title: string;
  gender: "female" | "male";
  description: string;
  avatarSeed: string;
}

export const INTERVIEWER_PERSONAS: InterviewerPersona[] = [
  {
    id: "elena",
    name: "Dr. Elena Vance",
    title: "Principal Bar-Raiser",
    gender: "female",
    description: "Rigorous, analytical, calm bar-raiser probing mathematical depth and edge cases.",
    avatarSeed: "elena",
  },
  {
    id: "alex",
    name: "Alex Chen",
    title: "Staff ML Architect",
    gender: "male",
    description: "Production infrastructure specialist focusing on latency SLAs, feature stores, and scale.",
    avatarSeed: "alex",
  },
  {
    id: "sarah",
    name: "Sarah Jenkins",
    title: "Senior Applied Scientist",
    gender: "female",
    description: "Balanced, thorough evaluator assessing statistical grounding, drift, and ML algorithms.",
    avatarSeed: "sarah",
  },
];

class InterviewerVoiceManager {
  private voices: SpeechSynthesisVoice[] = [];
  private isLoaded = false;
  private lockedVoice: SpeechSynthesisVoice | null = null;
  private lockedPersonaId: string = "elena";
  private animInterval: any = null;
  private keepAliveTimer: any = null;
  private activeUtterance: SpeechSynthesisUtterance | null = null;

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.initVoices();
    }
  }

  private initVoices(): void {
    const load = () => {
      this.voices = window.speechSynthesis.getVoices();
      if (this.voices.length > 0) {
        this.isLoaded = true;
        this.resolveAndLockVoice(this.lockedPersonaId);
      }
    };

    load();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.onvoiceschanged = load;
    }
  }

  public setPersona(personaId: string): void {
    this.lockedPersonaId = personaId;
    if (typeof window !== "undefined") {
      sessionStorage.setItem("ai_interviewer_persona", personaId);
    }
    this.resolveAndLockVoice(personaId);
  }

  public getPersona(): InterviewerPersona {
    const saved = typeof window !== "undefined" ? sessionStorage.getItem("ai_interviewer_persona") : null;
    const id = saved || this.lockedPersonaId;
    return INTERVIEWER_PERSONAS.find((p) => p.id === id) || INTERVIEWER_PERSONAS[0];
  }

  private resolveAndLockVoice(personaId: string): SpeechSynthesisVoice | null {
    if (this.voices.length === 0) return null;

    const persona = INTERVIEWER_PERSONAS.find((p) => p.id === personaId) || INTERVIEWER_PERSONAS[0];
    const isMale = persona.gender === "male";

    const englishVoices = this.voices.filter((v) => v.lang.startsWith("en"));
    if (englishVoices.length === 0) return this.voices[0] || null;

    let selected: SpeechSynthesisVoice | undefined;

    if (isMale) {
      // Natural male English voices
      selected = englishVoices.find(
        (v) =>
          v.name.includes("Google UK English Male") ||
          v.name.includes("Daniel") ||
          v.name.includes("Guy") ||
          v.name.includes("Arthur") ||
          v.name.includes("Male") ||
          v.name.includes("Natural - English (United States) - Guy")
      );
    } else {
      // Natural female English voices
      selected = englishVoices.find(
        (v) =>
          v.name.includes("Google US English") ||
          v.name.includes("Samantha") ||
          v.name.includes("Jenny") ||
          v.name.includes("Victoria") ||
          v.name.includes("Natural - English (United States) - Jenny") ||
          v.name.includes("Female")
      );
    }

    if (!selected) {
      selected = englishVoices.find((v) => v.name.includes("Natural") || v.name.includes("Google")) || englishVoices[0];
    }

    this.lockedVoice = selected || null;
    return this.lockedVoice;
  }

  public async getLockedVoice(): Promise<SpeechSynthesisVoice | null> {
    if (this.lockedVoice) return this.lockedVoice;

    // Wait up to 1 second for voices to populate if loading asynchronously
    if (!this.isLoaded && typeof window !== "undefined" && "speechSynthesis" in window) {
      await new Promise<void>((resolve) => {
        let attempts = 0;
        const check = () => {
          attempts++;
          this.voices = window.speechSynthesis.getVoices();
          if (this.voices.length > 0 || attempts >= 10) {
            this.isLoaded = true;
            this.resolveAndLockVoice(this.lockedPersonaId);
            resolve();
          } else {
            setTimeout(check, 100);
          }
        };
        check();
      });
    }

    return this.resolveAndLockVoice(this.lockedPersonaId);
  }

  public async speak(
    text: string,
    callbacks?: {
      onStart?: () => void;
      onEnd?: () => void;
      onFrequency?: (level: number) => void;
    }
  ): Promise<void> {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    this.cancel();

    // Strip markdown formatting symbols for natural speech
    const cleanText = text
      .replace(/[*_#`[\]()]/g, "")
      .replace(/--.*$/gm, "")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleanText) return;

    // Unpause speech synthesis in case Chromium was stuck in paused state
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }

    const voice = await this.getLockedVoice();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (voice) {
      utterance.voice = voice;
    }
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Keep persistent references to avoid V8 garbage collection mid-speech
    this.activeUtterance = utterance;
    (window as any).__activeSpeechUtterance = utterance;

    utterance.onstart = () => {
      callbacks?.onStart?.();

      // Simulate frequency fluctuation for avatar halo visualizer
      if (callbacks?.onFrequency) {
        this.animInterval = setInterval(() => {
          const fakeFreq = 30 + Math.floor(Math.random() * 55);
          callbacks.onFrequency?.(fakeFreq);
        }, 120);
      }

      // Chromium keepalive: SpeechSynthesis can stall after 15 seconds unless resumed
      if (this.keepAliveTimer) clearInterval(this.keepAliveTimer);
      this.keepAliveTimer = setInterval(() => {
        if (typeof window !== "undefined" && "speechSynthesis" in window) {
          if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          }
        }
      }, 9000);
    };

    const cleanup = () => {
      if (this.animInterval) {
        clearInterval(this.animInterval);
        this.animInterval = null;
      }
      if (this.keepAliveTimer) {
        clearInterval(this.keepAliveTimer);
        this.keepAliveTimer = null;
      }
      this.activeUtterance = null;
      if (typeof window !== "undefined") {
        (window as any).__activeSpeechUtterance = null;
      }
      callbacks?.onFrequency?.(0);
      callbacks?.onEnd?.();
    };

    utterance.onend = cleanup;
    utterance.onerror = (e) => {
      // In Chromium, 'interrupted' or 'canceled' errors are expected when cancelling
      cleanup();
    };

    window.speechSynthesis.speak(utterance);
  }

  public cancel(): void {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    if (this.animInterval) {
      clearInterval(this.animInterval);
      this.animInterval = null;
    }
    if (this.keepAliveTimer) {
      clearInterval(this.keepAliveTimer);
      this.keepAliveTimer = null;
    }
    this.activeUtterance = null;
    if (typeof window !== "undefined") {
      (window as any).__activeSpeechUtterance = null;
    }
  }
}

export const voiceManager = new InterviewerVoiceManager();
