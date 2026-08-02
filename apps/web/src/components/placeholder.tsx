/**
 * 未实现功能的占位页。
 *
 * 刻意写清楚"已完成什么、还差什么、属于哪个里程碑"，而不是显示一个空壳或
 * 假装可用的界面——演示时看到的东西必须和真实进度一致。
 */
export function Placeholder({
  title,
  milestone,
  done,
  todo,
}: {
  title: string;
  milestone: string;
  done: string[];
  todo: string[];
}) {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-baseline gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
          {milestone} 开发中
        </span>
      </div>

      <p className="mt-2 text-sm text-slate-600">
        此页面尚未实现。当前可用的完整链路在
        <a href="/lab" className="mx-1 underline underline-offset-2">
          解析实验台
        </a>
        中演示。
      </p>

      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <section>
          <h2 className="text-sm font-medium text-emerald-700">已完成</h2>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
            {done.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-emerald-600">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="text-sm font-medium text-slate-500">待实现</h2>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-500">
            {todo.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-slate-400">·</span>
                {item}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
