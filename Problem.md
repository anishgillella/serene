# RAG-Enabled Voice Agent Project

## 📋 Overview

Build a RAG-enabled voice agent that solves a personal problem in your life. Use **LiveKit Cloud** for hosting the server.

---

## 🎯 Objectives

- ✅ Create a voice agent with LiveKit that you can converse with on a custom (simple) frontend
- ✅ Transcribe speech in real time and maintain a live transcript
- ✅ Give your agent a personality—**spin a story**. Be creative. **Put time into this part!** (Behavioral evaluation)
- ✅ Make a **tool call of your choice** that fits in with the narrative
  - *Example:* Basketball coach agent → tool call for nearby courts
- ✅ Use RAG to enable the voice agent to answer questions from a large PDF document related to your story
  - *Example:* Basketball coach agent + PDF of Steve Kerr book → advice on OT strategies
- ⭐ **Bonus:** Deploy your agent on **AWS** instead of running locally

---

## 🔧 Technical Requirements

### 1️⃣ [Backend] LiveKit Setup

- Deploy a LiveKit server or use LiveKit Cloud for server hosting
- Build a LiveKit Agent capable of joining a room and having live conversations
- The agent can be hosted locally or on AWS (bonus points for AWS)
- Implement a voice agent pipeline with configurable **STT**, **LLM**, **TTS**, **VAD**

### 2️⃣ [Backend] RAG Over Uploaded PDF

- Enable the voice agent to retrieve information from a large, relevant PDF document
- Implement **Retrieval-Augmented Generation (RAG)** to answer questions about the PDF in **real-time voice conversation**
- Support queries about **specific facts in specific chapters** (not just keyword search or summarization)
- Use an **existing RAG framework**:
  - LangChain, LlamaIndex, or OpenAI's retrieval tools
  - Reference: [LiveKit Agents + External Data (Docs)](https://docs.livekit.io/agents/build/external-data/)

### 3️⃣ [Frontend] Chat Interface with Real-Time Transcription

Build a **React-based client** with:
- "Start Call" button
- **Live transcript** display (updates as participants speak)
- "End Call" button
- (Optional) **PDF upload button** to the frontend *if* it fits your UX flow

---

## ⚙️ Constraints

- Must use **LiveKit**
- Use any AI tools as needed (document them in README)

---

## 📦 Deliverables

Submit a single **Git repository** containing:

### 1. **Full Application Code**
- LiveKit Python backend (including RAG logic)
- React frontend
- Vector store implementation

### 2. **README.md**
- **Design Document** explaining:
  - End-to-end system architecture
  - RAG integration details
  - Tools/frameworks used
- **Setup Instructions** for local or web deployment

### 3. **Design Decisions & Assumptions**
- Document:
  - Trade-offs and limitations
  - Hosting assumptions
  - RAG assumptions (vector DB choice, chunking strategy, frameworks)
  - LiveKit agent design decisions

---

## 📤 Submission

**Share the GitHub repo with `farazs27@gmail.com` when complete**
