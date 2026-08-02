import { Placeholder } from "@/components/placeholder";

export default function ChatPage() {
  return (
    <Placeholder
      title="问答"
      milestone="M2-03"
      done={["带引用的生成与低置信度拒答（后端已实现，见 /lab）"]}
      todo={["多轮会话与历史记录", "SSE 流式输出", "引用详情与原文预览", "会话列表与切换"]}
    />
  );
}
