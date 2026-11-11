"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Database,
  FileText,
  FileUp,
  HardDrive,
  LoaderCircle,
  RefreshCw,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { deleteDemoDocument, fetchDemoDocuments, indexDemoDocument } from "@/lib/api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export default function KnowledgeBasePage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["demo-documents"],
    queryFn: fetchDemoDocuments,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => indexDemoDocument(file),
    onSuccess: (res) => {
      setUploadError(null);
      setUploadSuccess(`《${res.filename}》上传并切分索引成功，生成 ${res.chunk_count} 个向量切片！`);
      queryClient.invalidateQueries({ queryKey: ["demo-documents"] });
    },
    onError: (err: Error) => {
      setUploadSuccess(null);
      setUploadError(err.message || "文档上传解析失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => deleteDemoDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demo-documents"] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setUploadSuccess(null);
    uploadMutation.mutate(file);
    e.target.value = "";
  };

  const docs = data?.documents ?? [];
  const totalChunks = docs.reduce((acc, cur) => acc + cur.chunk_count, 0);

  return (
    <div className="space-y-6">
      {/* 顶部标题与操作 */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900">企业知识库管理</h1>
          <p className="mt-1 text-xs text-slate-500">
            支持 PDF / DOCX / Markdown / TXT 结构化解析、tiktoken 边界切片与 pgvector 向量入库
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-2xs hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`size-3.5 ${isFetching ? "animate-spin" : ""}`} />
            刷新
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.md,.markdown,.txt"
            onChange={handleFileChange}
            className="hidden"
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-blue-700 disabled:opacity-50"
          >
            {uploadMutation.isPending ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <FileUp className="size-4" />
            )}
            上传企业文档
          </button>
        </div>
      </div>

      {/* 提示信息 */}
      {uploadSuccess && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-800">
          <CheckCircle2 className="size-4 text-emerald-600 shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {uploadError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-800">
          <AlertCircle className="size-4 text-red-600 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* 统计指标卡片 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">已索引文档</span>
            <FileText className="size-4 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{docs.length}</div>
          <p className="mt-1 text-[11px] text-slate-400">支持 PDF/DOCX/MD/TXT</p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">向量切片总量</span>
            <Database className="size-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{totalChunks}</div>
          <p className="mt-1 text-[11px] text-slate-400">tiktoken 有界结构化切片</p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">向量存储引擎</span>
            <HardDrive className="size-4 text-purple-600" />
          </div>
          <div className="mt-2 text-lg font-bold text-slate-900">pgvector 0.8.6</div>
          <p className="mt-1 text-[11px] text-slate-400">HNSW 索引 · VECTOR(1024)</p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">检索中台策略</span>
            <RefreshCw className="size-4 text-amber-600" />
          </div>
          <div className="mt-2 text-lg font-bold text-slate-900">MimirQ 多路召回</div>
          <p className="mt-1 text-[11px] text-slate-400">BM25 + 向量 + Rerank 热切</p>
        </div>
      </div>

      {/* 文档列表表格 */}
      <div className="rounded-lg border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-3.5 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">知识库文档清单</h2>
          <span className="text-xs text-slate-500">共 {docs.length} 份文档已就绪</span>
        </div>

        {isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <LoaderCircle className="size-6 animate-spin text-blue-600" />
          </div>
        ) : isError ? (
          <div className="flex h-48 flex-col items-center justify-center text-center p-6">
            <AlertCircle className="size-8 text-red-500" />
            <p className="mt-2 text-sm text-slate-700">加载文档列表失败</p>
            <p className="text-xs text-slate-400 mt-1">请确认后端服务正在运行</p>
          </div>
        ) : docs.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center text-center p-6">
            <FileText className="size-8 text-slate-300" />
            <p className="mt-2 text-sm text-slate-600">知识库中暂无已索引文档</p>
            <p className="text-xs text-slate-400 mt-1">点击右上角“上传企业文档”进行索引切片</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="border-b border-slate-100 bg-slate-50/70 text-[11px] uppercase text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">文档名称</th>
                  <th className="px-5 py-3 font-medium">格式</th>
                  <th className="px-5 py-3 font-medium">文件大小</th>
                  <th className="px-5 py-3 font-medium">切片数</th>
                  <th className="px-5 py-3 font-medium">状态</th>
                  <th className="px-5 py-3 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/50 transition">
                    <td className="px-5 py-3.5 font-medium text-slate-900 flex items-center gap-2">
                      <FileText className="size-4 text-blue-600 shrink-0" />
                      <span>{doc.filename}</span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[11px] text-slate-500">
                      {doc.mime_type.split("/")[1] || "text"}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {formatBytes(doc.size_bytes)}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="rounded bg-blue-50 px-2 py-0.5 font-semibold text-blue-700">
                        {doc.chunk_count} chunks
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                        <span className="size-1.5 rounded-full bg-emerald-500" />
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      <Link
                        href="/chat"
                        className="inline-flex items-center gap-1 rounded px-2.5 py-1 font-medium text-blue-600 hover:bg-blue-50"
                      >
                        问答直达
                        <ArrowRight className="size-3" />
                      </Link>
                      <button
                        type="button"
                        onClick={() => {
                          if (confirm(`确认删除文档《${doc.filename}》及其切片？`)) {
                            deleteMutation.mutate(doc.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="inline-flex items-center rounded p-1 text-slate-400 hover:text-red-600"
                        title="删除文档"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
