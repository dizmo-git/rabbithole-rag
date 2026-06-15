import Layout from "./components/Layout";
import { LLMInputGroup } from "./components/LLMInputGroup";

export default function App() {
  return (
    <Layout>
      <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6">
        <h1 className="mb-6 text-2xl font-bold">Rabbithole RAG</h1>
        <div></div>
        <LLMInputGroup></LLMInputGroup>
      </div>
    </Layout>
  );
}
