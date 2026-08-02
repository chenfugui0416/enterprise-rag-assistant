"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Braces, CheckCircle2, ChevronRight, FileArchive, FileText, Gauge, Hash, Layers3, LoaderCircle, Play, RotateCcw, Upload, X } from "lucide-react";
import { ChangeEvent, DragEvent, useMemo, useRef, useState } from "react";

import {
  DocumentChunk,
  ParsedBlock,
  fetchHealth,
  previewDocument,
} from "@/lib/api";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".md", ".markdown", ".txt"];
const KIND_LABELS: Record<ParsedBlock["kind"], string> = {
  page: "页面",
  heading: "标题",
  paragraph: "段落",
  table: "表格",
  code: "代码",
  text: "文本",
};

type ResultTab = "blocks" | "chunks";

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [maxTokens, setMaxTokens] = useState(512);
  const [overlap, setOverlap] = useState(64);
  const [activeTab, setActiveTab] = useState<ResultTab>("chunks");
  const [isDragging, setIsDragging] = useState(false);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    retry: 1,
  });
  const preview = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("请先选择文档。");
      return previewDocument(file, maxTokens, overlap);
    },
    onSuccess: () => setActiveTab("chunks"),
  });

  const processFile = (selected: File | undefined) => {
    if (!selected) return;
    setFile(selected);
    preview.reset();
  };

  const onFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    processFile(event.target.files?.[0]);
    event.target.value = "";
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    processFile(event.dataTransfer.files?.[0]);
  };

  const updateMaxTokens = (value: number) => {
    const next = Math.min(4096, Math.max(32, value));
    setMaxTokens(next);
    setOverlap((current) => Math.min(current, next - 1));
    preview.reset();
  };

  const updateOverlap = (value: number) => {
    setOverlap(Math.min(maxTokens - 1, Math.max(0, value)));
    preview.reset();
  };

  return (
    <div>

      <div>
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">文档解析与结构化切分</h2>
            <div className="mt-2 flex items-center gap-2 text-xs text-[#66736d]">
              <span>原始文档</span>
              <ChevronRight size={13} aria-hidden="true" />
              <span>解析块</span>
              <ChevronRight size={13} aria-hidden="true" />
              <span>Token 切片</span>
            </div>
          </div>
          {preview.data && (
            <button
              type="button"
              onClick={() => preview.reset()}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-[#cbd4cf] bg-white px-3 text-sm font-medium hover:bg-[#f0f3f1]"
            >
              <RotateCcw size={15} aria-hidden="true" />
              重置结果
            </button>
          )}
        </div>

        <section className="grid items-start gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
          <div className="overflow-hidden rounded-lg border border-[#d8dfdb] bg-white">
            <div className="border-b border-[#e5e9e7] px-5 py-4">
              <h3 className="text-sm font-semibold">输入文档</h3>
            </div>
            <div className="space-y-6 p-5">
              <div
                onDragEnter={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDragging(false)}
                onDrop={onDrop}
                className={`relative grid min-h-40 place-items-center border border-dashed p-5 text-center transition-colors ${
                  isDragging
                    ? "border-[#237a57] bg-[#edf8f2]"
                    : "border-[#bfc9c4] bg-[#fafbfa]"
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept={ACCEPTED_EXTENSIONS.join(",")}
                  onChange={onFileInput}
                  className="sr-only"
                  aria-label="选择文档"
                />
                {file ? (
                  <div className="min-w-0">
                    <FileArchive className="mx-auto text-[#237a57]" size={28} aria-hidden="true" />
                    <p className="mt-3 break-all text-sm font-medium">{file.name}</p>
                    <p className="mt-1 text-xs text-[#66736d]">{formatBytes(file.size)}</p>
                    <button
                      type="button"
                      onClick={() => {
                        setFile(null);
                        preview.reset();
                      }}
                      title="移除文档"
                      aria-label="移除文档"
                      className="absolute right-2 top-2 grid size-8 place-items-center rounded-md text-[#66736d] hover:bg-[#e8ecea] hover:text-[#17211d]"
                    >
                      <X size={16} aria-hidden="true" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="group"
                  >
                    <Upload
                      className="mx-auto text-[#237a57] group-hover:text-[#185c41]"
                      size={28}
                      aria-hidden="true"
                    />
                    <span className="mt-3 block text-sm font-medium">选择文档</span>
                    <span className="mt-1 block text-xs text-[#66736d]">
                      PDF · DOCX · Markdown · TXT，最大 50 MiB
                    </span>
                  </button>
                )}
              </div>

              {file && (
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-[#cbd4cf] text-sm font-medium hover:bg-[#f3f5f4]"
                >
                  <Upload size={15} aria-hidden="true" />
                  更换文档
                </button>
              )}

              <fieldset className="space-y-5">
                <legend className="text-sm font-semibold">切分参数</legend>
                <NumberControl
                  label="单块最大 Token"
                  value={maxTokens}
                  min={32}
                  max={4096}
                  step={32}
                  onChange={updateMaxTokens}
                />
                <NumberControl
                  label="重叠 Token"
                  value={overlap}
                  min={0}
                  max={Math.min(1024, maxTokens - 1)}
                  step={8}
                  onChange={updateOverlap}
                />
              </fieldset>

              <button
                type="button"
                onClick={() => preview.mutate()}
                disabled={!file || preview.isPending || health.isError}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-[#173f35] px-4 text-sm font-semibold text-white hover:bg-[#0f3028] disabled:cursor-not-allowed disabled:opacity-45"
              >
                {preview.isPending ? (
                  <LoaderCircle className="animate-spin" size={17} aria-hidden="true" />
                ) : (
                  <Play size={17} fill="currentColor" aria-hidden="true" />
                )}
                {preview.isPending ? "处理中" : "解析并切分"}
              </button>

              {preview.isError && (
                <div role="alert" className="border-l-2 border-[#d92d20] bg-[#fff5f4] px-3 py-2.5">
                  <p className="text-sm font-medium text-[#9f241b]">处理失败</p>
                  <p className="mt-1 text-xs leading-5 text-[#b42318]">
                    {preview.error instanceof Error ? preview.error.message : "未知错误"}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="min-w-0 overflow-hidden rounded-lg border border-[#d8dfdb] bg-white">
            {!preview.data && !preview.isPending && <EmptyResult />}
            {preview.isPending && <LoadingResult />}
            {preview.data && (
              <ResultViewer
                result={preview.data}
                activeTab={activeTab}
                onTabChange={setActiveTab}
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function NumberControl({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="flex items-center justify-between gap-3 text-xs text-[#53615a]">
        <span>{label}</span>
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className="h-8 w-20 rounded-md border border-[#cbd4cf] bg-white px-2 text-right font-mono text-xs text-[#17211d] outline-none focus:border-[#237a57] focus:ring-2 focus:ring-[#237a57]/15"
        />
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-3 w-full accent-[#237a57]"
      />
      <span className="mt-1 flex justify-between font-mono text-[10px] text-[#89938e]">
        <span>{min}</span>
        <span>{max}</span>
      </span>
    </label>
  );
}

function EmptyResult() {
  return (
    <div className="grid min-h-[620px] place-items-center px-6 py-16 text-center">
      <div>
        <div className="mx-auto grid size-12 place-items-center rounded-lg bg-[#eef2f0] text-[#53615a]">
          <Braces size={23} aria-hidden="true" />
        </div>
        <p className="mt-4 text-sm font-medium">等待处理结果</p>
        <p className="mt-1 text-xs text-[#748079]">解析块和 Token 切片将在这里显示</p>
      </div>
    </div>
  );
}

function LoadingResult() {
  return (
    <div className="grid min-h-[620px] place-items-center px-6 py-16 text-center">
      <div>
        <LoaderCircle className="mx-auto animate-spin text-[#237a57]" size={28} aria-hidden="true" />
        <p className="mt-4 text-sm font-medium">正在解析文档</p>
        <p className="mt-1 text-xs text-[#748079]">读取结构并计算 Token</p>
      </div>
    </div>
  );
}

function ResultViewer({
  result,
  activeTab,
  onTabChange,
}: {
  result: Awaited<ReturnType<typeof previewDocument>>;
  activeTab: ResultTab;
  onTabChange: (tab: ResultTab) => void;
}) {
  const stats = useMemo(
    () => [
      { label: "解析块", value: result.block_count, icon: FileText },
      { label: "Chunk", value: result.chunk_count, icon: Layers3 },
      { label: "总 Token", value: result.total_tokens, icon: Hash },
      { label: "字符数", value: result.character_count, icon: Gauge },
    ],
    [result],
  );

  return (
    <>
      <div className="border-b border-[#e5e9e7] px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={17} className="shrink-0 text-[#237a57]" aria-hidden="true" />
              <h3 className="truncate text-sm font-semibold">{result.filename}</h3>
            </div>
            <p className="mt-1 pl-6 text-xs text-[#66736d]">
              {formatBytes(result.size_bytes)} · {result.media_type}
              {result.page_count ? ` · ${result.page_count} 页` : ""}
              {result.encoding ? ` · ${result.encoding}` : ""}
            </p>
          </div>
          <span className="rounded-md bg-[#edf8f2] px-2 py-1 font-mono text-[11px] font-medium text-[#237a57]">
            {result.config.max_tokens} / overlap {result.config.chunk_overlap}
          </span>
        </div>
      </div>

      <dl className="grid grid-cols-2 border-b border-[#e5e9e7] sm:grid-cols-4">
        {stats.map(({ label, value, icon: Icon }, index) => (
          <div
            key={label}
            className={`border-[#e5e9e7] px-5 py-4 ${
              index % 2 === 0 ? "border-r" : ""
            } sm:border-r sm:last:border-r-0`}
          >
            <dt className="flex items-center gap-1.5 text-[11px] text-[#66736d]">
              <Icon size={13} aria-hidden="true" />
              {label}
            </dt>
            <dd className="mt-1 font-mono text-lg font-semibold">{value.toLocaleString("zh-CN")}</dd>
          </div>
        ))}
      </dl>

      <div className="border-b border-[#e5e9e7] px-5 pt-3">
        <div className="inline-flex rounded-md bg-[#eef2f0] p-1" role="tablist" aria-label="结果视图">
          <TabButton
            active={activeTab === "blocks"}
            onClick={() => onTabChange("blocks")}
            label={`解析块 ${result.block_count}`}
          />
          <TabButton
            active={activeTab === "chunks"}
            onClick={() => onTabChange("chunks")}
            label={`Chunk ${result.chunk_count}`}
          />
        </div>
      </div>

      <div className="max-h-[650px] overflow-y-auto p-4 sm:p-5">
        {activeTab === "blocks" ? (
          <div className="space-y-3">
            {result.blocks.map((block) => (
              <BlockRow key={block.index} block={block} />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {result.chunks.map((chunk) => (
              <ChunkRow key={chunk.index} chunk={chunk} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`h-8 rounded px-3 text-xs font-medium ${
        active ? "bg-white text-[#17211d] shadow-sm" : "text-[#66736d] hover:text-[#17211d]"
      }`}
    >
      {label}
    </button>
  );
}

function BlockRow({ block }: { block: ParsedBlock }) {
  return (
    <article className="rounded-md border border-[#dfe5e2] bg-white px-4 py-3">
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <span className="font-mono font-semibold text-[#237a57]">BLOCK {block.index}</span>
        <span className="rounded bg-[#eef2f0] px-1.5 py-0.5 text-[#53615a]">
          {KIND_LABELS[block.kind]}
        </span>
        <SourceLabels pageNumber={block.page_number} sectionTitle={block.section_title} />
      </div>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-[#2d3933]">
        {block.text}
      </p>
    </article>
  );
}

function ChunkRow({ chunk }: { chunk: DocumentChunk }) {
  return (
    <article className="rounded-md border border-[#dfe5e2] bg-white px-4 py-3">
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <span className="font-mono font-semibold text-[#237a57]">CHUNK {chunk.index}</span>
        <span className="rounded bg-[#e8f1ff] px-1.5 py-0.5 font-mono text-[#175cd3]">
          {chunk.token_count} Token
        </span>
        <SourceLabels pageNumber={chunk.page_number} sectionTitle={chunk.section_title} />
        <span className="ml-auto text-[#748079]">
          来源 {formatSourceBlocks(chunk.source_block_indices)}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-[#2d3933]">
        {chunk.text}
      </p>
    </article>
  );
}

function SourceLabels({
  pageNumber,
  sectionTitle,
}: {
  pageNumber: number | null;
  sectionTitle: string | null;
}) {
  return (
    <>
      {pageNumber !== null && <span className="text-[#66736d]">第 {pageNumber} 页</span>}
      {sectionTitle && <span className="max-w-52 truncate text-[#66736d]">{sectionTitle}</span>}
    </>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

function formatSourceBlocks(indices: number[]) {
  if (indices.length === 0) return "—";
  if (indices.length === 1) return `Block ${indices[0]}`;
  return `Block ${indices[0]}–${indices.at(-1)}`;
}
