import { redirect } from "next/navigation";

/** 根路径不承载内容：已登录进知识库，未登录会被 AuthGuard 送到登录页。 */
export default function RootPage() {
  redirect("/kb");
}
