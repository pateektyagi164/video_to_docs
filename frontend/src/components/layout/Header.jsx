import { BrainCircuit } from 'lucide-react';

export default function Header() {
  return (
    <header className="w-full max-w-4xl flex items-center gap-3 mb-12 mt-8">
      <BrainCircuit className="w-10 h-10 text-emerald-500" />
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">AI Multimodal Extractor</h1>
        <p className="text-gray-400 text-sm">Deep Video Knowledge Synthesis</p>
      </div>
    </header>
  );
}