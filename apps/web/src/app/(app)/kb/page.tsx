import { Placeholder } from "@/components/placeholder";

export default function KnowledgeBasePage() {
  return (
    <Placeholder
      title="知识库"
      milestone="M2-02"
      done={["认证与权限（登录、角色、会话）"]}
      todo={[
        "创建、查看、删除知识库",
        "上传 PDF / DOCX / Markdown / TXT",
        "展示解析与索引状态",
        "文档级权限与删除链路",
      ]}
    />
  );
}
