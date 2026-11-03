/**
 * Interviewer Voice & Persona Manager (2026 Edition).
 * Delivers deterministic voice synthesis, speech naturalization for technical terms,
 * and audio-reactive visualization events.
 */

export interface InterviewerPersona {
  id: string;
  name: string;
  title: string;
  gender: "female" | "male";
  archetype: string;
  description: string;
  avatarSeed: string;
  avatarImage: string;
  accent: string;
  speakingStyle: string;
}

export const INTERVIEWER_PERSONAS: InterviewerPersona[] = [
  {
    id: "elena",
    name: "Dr. Elena Vance",
    title: "Principal Bar-Raiser",
    gender: "female",
    archetype: "FAANG / Tier-1 Tech Bar-Raiser",
    description: "Rigorous, calm, and analytical. Deeply probes mathematical grounding, algorithmic boundaries, and failure modes.",
    avatarSeed: "elena",
    avatarImage: "/avatars/elena.jpg",
    accent: "US English",
    speakingStyle: "Composed, precise, insightful",
  },
  {
    id: "alex",
    name: "Alex Chen",
    title: "Staff ML Infrastructure Architect",
    gender: "male",
    archetype: "Production Systems & Distributed Scale",
    description: "Practical systems engineer obsessed with p99 latency SLAs, streaming feature pipelines, and high-throughput model serving.",
    avatarSeed: "alex",
    avatarImage: "/avatars/alex.jpg",
    accent: "US / International English",
    speakingStyle: "Energetic, systems-focused, collaborative",
  },
  {
    id: "sarah",
    name: "Sarah Jenkins",
    title: "Senior Staff Applied Scientist",
    gender: "female",
    archetype: "Applied ML & Experimentation Lead",
    description: "Warm yet uncompromising mentor focusing on business-metric alignment, statistical rigor, data leakage, and candidate reasoning.",
    avatarSeed: "sarah",
    avatarImage: "/avatars/sarah.jpg",
    accent: "US English",
    speakingStyle: "Warm, encouraging, rigorous",
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
      // Prioritize modern natural / high-clarity male voices
      selected = englishVoices.find(
        (v) =>
          v.name.includes("Natural") && (v.name.includes("Guy") || v.name.includes("David") || v.name.includes("Christopher") || v.name.includes("Eric"))
      ) || englishVoices.find(
        (v) =>
          v.name.includes("Google UK English Male") ||
          v.name.includes("Daniel") ||
          v.name.includes("Guy") ||
          v.name.includes("Arthur") ||
          v.name.includes("Male")
      );
    } else {
      // Prioritize modern natural / high-clarity female voices
      selected = englishVoices.find(
        (v) =>
          v.name.includes("Natural") && (v.name.includes("Jenny") || v.name.includes("Aria") || v.name.includes("Michelle") || v.name.includes("Ava"))
      ) || englishVoices.find(
        (v) =>
          v.name.includes("Google US English") ||
          v.name.includes("Samantha") ||
          v.name.includes("Jenny") ||
          v.name.includes("Victoria") ||
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

  /**
   * Preprocesses technical jargon, math formulas, and code symbols for natural spoken cadence.
   */
  public naturalizeTextForSpeech(text: string): string {
    return text
      .replace(/```[\s\S]*?```/g, " [I've shared the code sample in your editor.] ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/O\(([A-Za-z0-9_\^\*\+\s]+)\)/gi, "O of $1")
      .replace(/p99/gi, "P 99")
      .replace(/p95/gi, "P 95")
      .replace(/p50/gi, "P 50")
      .replace(/\bQPS\b/g, "Q P S")
      .replace(/\bSLA\b/g, "S L A")
      .replace(/\bSLO\b/g, "S L O")
      .replace(/\bSQL\b/g, "sequel")
      .replace(/\bLoRA\b/g, "low-ra")
      .replace(/\bQLoRA\b/g, "cue low-ra")
      .replace(/\bLLM\b/g, "L L M")
      .replace(/\bLLMs\b/g, "L L Ms")
      .replace(/\bRAG\b/g, "rag")
      .replace(/[*_#\[\]()]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
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

    const cleanText = this.naturalizeTextForSpeech(text);
    if (!cleanText) return;

    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }

    const voice = await this.getLockedVoice();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (voice) {
      utterance.voice = voice;
    }
    utterance.rate = 1.02;
    utterance.pitch = 1.0;

    this.activeUtterance = utterance;
    (window as any).__activeSpeechUtterance = utterance;

    utterance.onstart = () => {
      callbacks?.onStart?.();

      // Fluid sinusoidal audio wave simulation for reactive halo
      let phase = 0;
      if (callbacks?.onFrequency) {
        this.animInterval = setInterval(() => {
          phase += 0.4;
          const base = 40 + Math.sin(phase) * 20;
          const jitter = Math.random() * 25;
          const level = Math.min(100, Math.max(15, Math.round(base + jitter)));
          callbacks.onFrequency?.(level);
        }, 80);
      }

      // Chromium keepalive: SpeechSynthesis can stall after 14s unless gently pulsed
      if (this.keepAliveTimer) clearInterval(this.keepAliveTimer);
      this.keepAliveTimer = setInterval(() => {
        if (typeof window !== "undefined" && "speechSynthesis" in window) {
          if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          }
        }
      }, 8000);
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
    utterance.onerror = () => {
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
