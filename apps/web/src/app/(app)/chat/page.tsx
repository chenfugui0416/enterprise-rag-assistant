"use client";

import { useMutation } from "@tanstack/react-query";
import {
  Activity,
  Bot,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Layers,
  LoaderCircle,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Timer,
  User,
} from "lucide-react";
import { useState } from "react";

import { HistoryMessage, queryDemoKnowledgeBase, QueryResponse } from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  responseMeta?: QueryResponse;
  timestamp: string;
}

const SAMPLE_PROMPTS = [
  { label: "员工年假制度", question: "正式员工每年有多少天带薪年假？" },
  { label: "出差住宿标准", question: "出差住在一线城市，每晚住宿费上限是多少？" },
  { label: "防幻觉负样本", question: "公司的年终奖具体怎么计算？" },
  { label: "Agent 工具协同", question: "连续出差 3 天一线城市住宿上限总共是多少？（请计算 600 * 3）" },
];

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [useAgent, setUseAgent] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  const chatMutation = useMutation({
    mutationFn: ({ questionText, history }: { questionText: string; history: HistoryMessage[] }) =>
      queryDemoKnowledgeBase(questionText, 5, useAgent, history),
    onSuccess: (data) => {
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer,
        responseMeta: data,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    },
  });

  const handleSend = (textToSend?: string) => {
    const q = (textToSend ?? input).trim();
    if (!q || chatMutation.isPending) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: q,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    };

    const historyPayload: HistoryMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    chatMutation.mutate({ questionText: q, history: historyPayload });
  };

  const toggleCitation = (msgId: string) => {
    setExpandedCitations((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const toggleSteps = (msgId: string) => {
    setExpandedSteps((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div className="flex h-[calc(100vh-8.5rem)] flex-col gap-4">
      {/* 顶部控制栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-xs">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-md bg-blue-50 text-blue-700">
            <Sparkles className="size-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900">企业级知识库问答与编排</h1>
            <p className="text-xs text-slate-500">
              MimirQ 混合检索接入 · 全链路耗时追踪 · 100% 防幻觉安全拒答
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Agent 模式切换开关 */}
          <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              onClick={() => setUseAgent(false)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                !useAgent
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              标准 RAG 模式
            </button>
            <button
              type="button"
              onClick={() => setUseAgent(true)}
              className={`inline-flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition ${
                useAgent
                  ? "bg-blue-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Terminal className="size-3" />
              ReAct Agent 模式
            </button>
          </div>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              <RotateCcw className="size-3.5" />
              清空对话
            </button>
          )}
        </div>
      </div>

      {/* 对话消息区 */}
      <div className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/50 p-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-blue-100 text-blue-600">
              <Bot className="size-7" />
            </div>
            <h2 className="mt-4 text-base font-medium text-slate-800">
              企业级知识库助手已就绪
            </h2>
            <p className="mt-1.5 max-w-md text-xs text-slate-500">
              当前支持基于企业制度文档（员工手册、差旅规范、IT 安全）精准答疑。点击下方预置问题体验多路召回与防幻觉机制：
            </p>

            {/* 样例快捷提问 */}
            <div className="mt-6 flex max-w-lg flex-wrap justify-center gap-2">
              {SAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt.label}
                  type="button"
                  onClick={() => handleSend(prompt.question)}
                  className="rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-xs text-slate-700 shadow-2xs transition hover:border-blue-400 hover:bg-blue-50/50 hover:text-blue-700"
                >
                  <span className="font-medium text-blue-600">{prompt.label}：</span>
                  {prompt.question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-xs">
                  <Bot className="size-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-xl px-4 py-3 shadow-xs ${
                  msg.role === "user"
                    ? "bg-slate-900 text-white"
                    : "border border-slate-200 bg-white text-slate-900"
                }`}
              >
                {/* 消息正文 */}
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.content}
                </div>

                {/* Assistant 增强指标与证据卡片 */}
                {msg.role === "assistant" && msg.responseMeta && (
                  <div className="mt-3.5 space-y-2.5 border-t border-slate-100 pt-3">
                    {/* 防幻觉拒答警示条 */}
                    {msg.responseMeta.refused && (
                      <div className="flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 border border-amber-200/60">
                        <ShieldAlert className="size-4 shrink-0 text-amber-600" />
                        <span>【防幻觉拦截】知识库中无可靠语料依据，系统已触发确定性拒答，杜绝编造企业事实。</span>
                      </div>
                    )}

                    {!msg.responseMeta.refused && (
                      <div className="flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800 border border-emerald-200/60">
                        <ShieldCheck className="size-4 shrink-0 text-emerald-600" />
                        <span>【证据充分】答案已基于知识库权威切片完成上下文 Grounding 严格对齐。</span>
                      </div>
                    )}

                    {/* 全链路可观测性 Telemetry Badge */}
                    {msg.responseMeta.execution_trace && (
                      <div className="flex flex-wrap items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600 border border-slate-200">
                        <span className="flex items-center gap-1 font-semibold text-blue-700">
                          <Activity className="size-3.5" />
                          {msg.responseMeta.execution_trace.retrieval_mode === "mimirq_hybrid"
                            ? "MimirQ 混合检索"
                            : msg.responseMeta.execution_trace.retrieval_mode === "agent_react"
                            ? "ReAct 智能编排"
                            : "Dense 密集向量"}
                        </span>
                        <span className="text-slate-300">|</span>
                        <span className="flex items-center gap-1">
                          <Timer className="size-3 text-slate-400" />
                          总耗时: {msg.responseMeta.execution_trace.total_duration_ms}ms
                        </span>
                        <span>· 检索: {msg.responseMeta.execution_trace.retrieval_duration_ms}ms</span>
                        <span>· 模型: {msg.responseMeta.execution_trace.llm_duration_ms}ms</span>
                        {msg.responseMeta.execution_trace.top_score !== null && (
                          <span>· 最高分: {msg.responseMeta.execution_trace.top_score}</span>
                        )}
                      </div>
                    )}

                    {/* Agent 执行步骤（ReAct 模式展示） */}
                    {msg.responseMeta.agent_steps && msg.responseMeta.agent_steps.length > 0 && (
                      <div className="rounded-md border border-slate-200 bg-slate-50/70 p-2.5 text-xs">
                        <button
                          type="button"
                          onClick={() => toggleSteps(msg.id)}
                          className="flex w-full items-center justify-between font-medium text-slate-700 hover:text-slate-900"
                        >
                          <span className="flex items-center gap-1.5 text-blue-700 font-semibold">
                            <Terminal className="size-3.5" />
                            Agent 工具编排轨迹 ({msg.responseMeta.agent_steps.length} 步)
                          </span>
                          {expandedSteps[msg.id] ? (
                            <ChevronDown className="size-3.5" />
                          ) : (
                            <ChevronRight className="size-3.5" />
                          )}
                        </button>

                        {expandedSteps[msg.id] && (
                          <div className="mt-2.5 space-y-2 border-t border-slate-200 pt-2 font-mono text-[11px]">
                            {msg.responseMeta.agent_steps.map((st) => (
                              <div key={st.index} className="rounded bg-white p-2 border border-slate-200">
                                <div className="text-blue-600 font-bold">
                                  #{st.index} 调用工具: {st.tool_name}
                                </div>
                                <div className="text-slate-500 mt-0.5">入参: {st.arguments}</div>
                                <div className="text-slate-700 mt-1 max-h-24 overflow-y-auto whitespace-pre-wrap">
                                  返回: {st.result}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* 引用证据卡片 */}
                    {msg.responseMeta.citations && msg.responseMeta.citations.length > 0 && (
                      <div className="rounded-md border border-slate-200 bg-slate-50/70 p-2.5 text-xs">
                        <button
                          type="button"
                          onClick={() => toggleCitation(msg.id)}
                          className="flex w-full items-center justify-between font-medium text-slate-700 hover:text-slate-900"
                        >
                          <span className="flex items-center gap-1.5 font-semibold text-slate-800">
                            <BookOpen className="size-3.5 text-blue-600" />
                            引用来源与切片证据 ({msg.responseMeta.citations.length} 处)
                          </span>
                          {expandedCitations[msg.id] ? (
                            <ChevronDown className="size-3.5" />
                          ) : (
                            <ChevronRight className="size-3.5" />
                          )}
                        </button>

                        {expandedCitations[msg.id] && (
                          <div className="mt-2.5 grid gap-2 border-t border-slate-200 pt-2">
                            {msg.responseMeta.citations.map((c, idx) => (
                              <div
                                key={idx}
                                className="rounded bg-white p-2.5 border border-slate-200 shadow-2xs"
                              >
                                <div className="flex items-center justify-between font-medium text-slate-800">
                                  <span className="flex items-center gap-1">
                                    <Layers className="size-3 text-slate-400" />
                                    {c.document_name}
                                  </span>
                                  <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-700">
                                    得分 {c.score.toFixed(3)}
                                  </span>
                                </div>
                                {(c.page_number || c.section_title) && (
                                  <div className="mt-1 text-[11px] text-slate-500">
                                    {c.page_number ? `第 ${c.page_number} 页` : ""}
                                    {c.page_number && c.section_title ? " · " : ""}
                                    {c.section_title}
                                  </div>
                                )}
                                <p className="mt-1.5 text-slate-600 italic">
                                  &ldquo;{c.content}&rdquo;
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {msg.role === "user" && (
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white shadow-xs">
                  <User className="size-4" />
                </div>
              )}
            </div>
          ))
        )}

        {chatMutation.isPending && (
          <div className="flex items-center gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-xs">
              <Bot className="size-4" />
            </div>
            <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 shadow-xs">
              <LoaderCircle className="size-4 animate-spin text-blue-600" />
              <span>
                {useAgent ? "ReAct Agent 正在规划多步工具调用..." : "正在进行多路召回与引用生成..."}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 底部输入框 */}
      <div className="rounded-lg border border-slate-200 bg-white p-2 shadow-xs">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              useAgent
                ? "输入复杂问题（如结合政策计算费用，Agent 会自主调用检索与计算工具）..."
                : "输入制度、年假、差旅相关问题..."
            }
            disabled={chatMutation.isPending}
            className="flex-1 rounded-md px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden"
          />
          <button
            type="submit"
            disabled={!input.trim() || chatMutation.isPending}
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-blue-600 px-4 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:opacity-40"
          >
            {chatMutation.isPending ? (
              <LoaderCircle className="size-3.5 animate-spin" />
            ) : (
              <Send className="size-3.5" />
            )}
            发送
          </button>
        </form>
      </div>
    </div>
  );
}
