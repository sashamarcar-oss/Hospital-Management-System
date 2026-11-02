import { useMemo, useState } from "react";
import { ArrowLeft, Check, CheckCheck, MessageSquarePlus, Pencil, Search, Send, Trash2, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Conversation, Message, Paginated, UserBrief } from "@/lib/types";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useToast } from "@/hooks/use-toast";

const initials = (person?: UserBrief | null) => `${person?.first_name?.[0] ?? "?"}${person?.last_name?.[0] ?? ""}`;
const shortTime = (value?: string | null) => value ? new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
const dayLabel = (value: string) => {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return "Today";
  return date.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
};

export function MessagesPage() {
  const { user } = useAuth();
  const client = useQueryClient();
  const { success, error } = useToast();
  const [selected, setSelected] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileChatOpen, setMobileChatOpen] = useState(false);
  const [editingMessage, setEditingMessage] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.get<Paginated<Conversation>>("/messages/conversations/", { params: { page_size: 100 } }).then((r) => r.data.results),
    refetchInterval: 10_000,
  });
  const active = conversations.find((conversation) => conversation.id === selected) ?? conversations[0];
  const activePerson = active?.participants_details.find((person) => person.id !== user?.id);
  const { data: messages = [] } = useQuery({
    queryKey: ["conversation", active?.id],
    enabled: !!active,
    queryFn: () => api.get<Paginated<Message>>(`/messages/conversations/${active!.id}/messages/`, { params: { page_size: 100 } }).then((r) => r.data.results),
    refetchInterval: 5_000,
  });
  const { data: users = [], isFetching: searching } = useQuery({
    queryKey: ["message-users", query],
    enabled: searchOpen,
    queryFn: () => api.get<UserBrief[]>("/messages/conversations/staff/", { params: { search: query.trim() || undefined } }).then((r) => r.data),
  });
  const filteredConversations = useMemo(() => conversations.filter((conversation) => {
    const person = conversation.participants_details.find((item) => item.id !== user?.id);
    const label = `${person?.first_name ?? ""} ${person?.last_name ?? ""} ${conversation.last_message?.content ?? ""}`.toLowerCase();
    return label.includes(query.trim().toLowerCase());
  }), [conversations, query, user?.id]);

  const send = useMutation({
    mutationFn: () => api.post(`/messages/conversations/${active!.id}/messages/`, { content: draft.trim() }),
    onSuccess: () => {
      setDraft("");
      client.invalidateQueries({ queryKey: ["conversation", active?.id] });
      client.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (e) => error(getErrorMessage(e)),
  });
  const start = useMutation({
    mutationFn: (id: number) => api.post<Conversation>("/messages/conversations/", { participants: [id, user!.id] }).then((r) => r.data),
    onSuccess: (conversation) => {
      setSelected(conversation.id);
      setMobileChatOpen(true);
      setQuery("");
      setSearchOpen(false);
      client.invalidateQueries({ queryKey: ["conversations"] });
      success("Conversation ready");
    },
    onError: (e) => error(getErrorMessage(e, "Unable to start a conversation.")),
  });
  const edit = useMutation({
    mutationFn: () => api.patch(`/messages/${editingMessage}/`, { content: editDraft.trim() }),
    onSuccess: () => {
      setEditingMessage(null);
      setEditDraft("");
      client.invalidateQueries({ queryKey: ["conversation", active?.id] });
      client.invalidateQueries({ queryKey: ["conversations"] });
      success("Message updated");
    },
    onError: (e) => error(getErrorMessage(e, "Unable to edit this message.")),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/messages/${id}/`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["conversation", active?.id] });
      client.invalidateQueries({ queryKey: ["conversations"] });
      success("Message deleted");
    },
    onError: (e) => error(getErrorMessage(e, "Unable to delete this message.")),
  });

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-semibold tracking-tight">Messages</h1><p className="text-sm text-muted-foreground">Private conversations with hospital staff</p></div>
        <Button className="md:hidden" size="sm" onClick={() => { setSearchOpen((open) => !open); setQuery(""); }}><MessageSquarePlus className="mr-2 size-4" />New chat</Button>
      </div>

      <div className="mx-auto grid h-[min(78dvh,820px)] min-h-[560px] w-full max-w-[1440px] overflow-hidden rounded-xl border bg-card shadow-sm max-md:h-[calc(100dvh-11rem)] max-md:min-h-[440px] md:grid-cols-[380px_minmax(0,1fr)]">
        <aside className={`${mobileChatOpen ? "hidden md:flex" : "flex"} min-h-0 flex-col border-r`}>
          <div className="flex items-center justify-between bg-[#075e54] px-4 py-4 text-white">
            <div className="flex items-center gap-3"><Avatar className="size-10 border border-white/20"><AvatarImage src={user?.profile_photo ?? undefined} /><AvatarFallback className="bg-white/20 text-white">{initials(user)}</AvatarFallback></Avatar><div><p className="font-semibold">Chats</p><p className="text-xs text-white/70">Radiant staff</p></div></div>
            <Button aria-label="Start new chat" size="icon" variant="ghost" className="text-white hover:bg-white/10 hover:text-white" onClick={() => { setSearchOpen((open) => !open); setQuery(""); }}><MessageSquarePlus className="size-5" /></Button>
          </div>
          <div className="border-b bg-muted/40 p-3">
            <div className="relative"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="h-9 rounded-full border-0 bg-background pl-9" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={searchOpen ? "Find a staff member" : "Search chats"} /></div>
          </div>
          {searchOpen ? <div className="min-h-0 flex-1 overflow-y-auto">
            <p className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Start a conversation</p>
            {searching ? <p className="p-4 text-sm text-muted-foreground">Loading staff…</p> : users.length ? users.map((person) => <button key={person.id} onClick={() => start.mutate(person.id)} disabled={start.isPending} className="flex w-full items-center gap-3 border-b px-4 py-3 text-left hover:bg-muted disabled:opacity-50"><Avatar><AvatarImage src={person.profile_photo ?? undefined} /><AvatarFallback>{initials(person)}</AvatarFallback></Avatar><span className="min-w-0"><span className="block truncate font-medium">{person.first_name} {person.last_name}</span><small className="text-muted-foreground">{person.role_name}</small></span></button>) : <p className="p-4 text-sm text-muted-foreground">No staff members found.</p>}
          </div> : <div className="min-h-0 flex-1 overflow-y-auto">
            {filteredConversations.map((conversation) => {
              const person = conversation.participants_details.find((item) => item.id !== user?.id);
              const isActive = active?.id === conversation.id;
              return <button key={conversation.id} onClick={() => { setSelected(conversation.id); setMobileChatOpen(true); }} className={`flex w-full items-center gap-3 border-b px-4 py-3 text-left transition-colors hover:bg-muted/70 ${isActive ? "bg-muted" : "bg-card"}`}>
                <Avatar className="size-12"><AvatarImage src={person?.profile_photo ?? undefined} /><AvatarFallback>{initials(person)}</AvatarFallback></Avatar>
                <span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-2"><span className="truncate font-medium">{person?.first_name} {person?.last_name}</span><small className={`shrink-0 text-xs ${conversation.unread_count ? "text-emerald-700" : "text-muted-foreground"}`}>{shortTime(conversation.last_message?.created_at)}</small></span><span className="mt-1 flex items-center justify-between gap-2"><span className="truncate text-sm text-muted-foreground">{conversation.last_message?.content || "No messages yet"}</span>{conversation.unread_count > 0 && <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[11px] font-semibold text-white">{conversation.unread_count}</span>}</span></span>
              </button>;
            })}
            {!filteredConversations.length && <p className="p-6 text-center text-sm text-muted-foreground">{conversations.length ? "No chats match your search." : "No conversations yet. Start a new chat with a colleague."}</p>}
          </div>}
        </aside>

        <main className={`${mobileChatOpen ? "flex" : "hidden md:flex"} min-w-0 flex-col`}>
          {active ? <>
            <header className="flex items-center gap-3 border-b bg-muted/30 px-3 py-3 md:px-5">
              <Button aria-label="Back to chats" size="icon" variant="ghost" className="md:hidden" onClick={() => setMobileChatOpen(false)}><ArrowLeft className="size-5" /></Button>
              <Avatar className="size-10"><AvatarImage src={activePerson?.profile_photo ?? undefined} /><AvatarFallback>{initials(activePerson)}</AvatarFallback></Avatar>
              <div className="min-w-0 flex-1"><p className="truncate font-semibold">{activePerson?.first_name} {activePerson?.last_name}</p><p className="truncate text-xs text-muted-foreground">{activePerson?.role_name || "Hospital staff"}</p></div>
              <div className="hidden items-center text-muted-foreground sm:flex"><span className="text-xs">Private conversation</span></div>
            </header>
            <div className="flex-1 space-y-2 overflow-y-auto bg-[#efeae2] bg-[radial-gradient(#d8d1c7_0.7px,transparent_0.7px)] [background-size:16px_16px] px-3 py-5 sm:px-6">
              {messages.length ? messages.map((message, index) => {
                const mine = message.sender === user?.id;
                const previous = messages[index - 1];
                const showDay = !previous || new Date(previous.created_at).toDateString() !== new Date(message.created_at).toDateString();
                return <div key={message.id}>
                  {showDay && <div className="my-4 flex justify-center"><span className="rounded-md bg-white/90 px-3 py-1 text-[11px] font-medium text-muted-foreground shadow-sm">{dayLabel(message.created_at)}</span></div>}
                  <div className={`flex ${mine ? "justify-end" : "justify-start"}`}><article className={`group relative max-w-[88%] rounded-lg px-3 py-2 shadow-sm sm:max-w-[75%] ${mine ? "rounded-tr-none bg-[#d9fdd3]" : "rounded-tl-none bg-white"}`}>
                    {editingMessage === message.id ? <form onSubmit={(event) => { event.preventDefault(); if (editDraft.trim()) edit.mutate(); }} className="min-w-[220px] space-y-2"><Input autoFocus value={editDraft} onChange={(event) => setEditDraft(event.target.value)} aria-label="Edit message" className="h-9 bg-white" /><div className="flex justify-end gap-1"><Button type="button" size="sm" variant="ghost" onClick={() => { setEditingMessage(null); setEditDraft(""); }}><X className="mr-1 size-3.5" />Cancel</Button><Button type="submit" size="sm" disabled={edit.isPending || !editDraft.trim()}><Check className="mr-1 size-3.5" />Save</Button></div></form> : <><p className="whitespace-pre-wrap break-words text-sm text-slate-800">{message.content}</p><div className="mt-1 flex items-center justify-end gap-1 text-[10px] text-slate-500"><time>{shortTime(message.created_at)}</time>{mine && <CheckCheck aria-label={message.is_read ? "Read" : "Sent"} className={`size-3.5 ${message.is_read ? "text-sky-600" : "text-slate-400"}`} />}</div>{mine && <div className="absolute -top-2 right-1 hidden gap-1 rounded-md bg-white p-1 shadow group-hover:flex group-focus-within:flex"><Button type="button" aria-label="Edit message" size="icon" variant="ghost" className="size-7" onClick={() => { setEditingMessage(message.id); setEditDraft(message.content); }}><Pencil className="size-3.5" /></Button><Button type="button" aria-label="Delete message" size="icon" variant="ghost" className="size-7 text-destructive" disabled={remove.isPending} onClick={() => { if (window.confirm("Delete this message?")) remove.mutate(message.id); }}><Trash2 className="size-3.5" /></Button></div>}</>}
                  </article></div>
                </div>;
              }) : <div className="flex h-full items-center justify-center"><p className="rounded-lg bg-white/90 px-4 py-2 text-center text-sm text-muted-foreground shadow-sm">This is the beginning of your conversation.</p></div>}
            </div>
            <form onSubmit={(event) => { event.preventDefault(); if (draft.trim()) send.mutate(); }} className="flex items-center gap-2 border-t bg-muted/30 px-3 py-3 sm:px-4">
              <div className="min-w-0 flex-1"><Input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Type a message" className="h-11 rounded-full border-0 bg-background px-4 shadow-sm" /></div>
              <Button type="submit" aria-label="Send message" size="icon" disabled={send.isPending || !draft.trim()} className="size-11 shrink-0 rounded-full bg-[#128c7e] text-white hover:bg-[#075e54]"><Send className="size-4" /></Button>
            </form>
          </> : <div className="m-auto hidden max-w-sm text-center md:block"><div className="mx-auto mb-5 flex size-20 items-center justify-center rounded-full bg-emerald-50 text-[#128c7e]"><MessageSquarePlus className="size-9" /></div><h2 className="text-xl font-medium">Your messages</h2><p className="mt-2 text-sm text-muted-foreground">Choose a conversation to continue chatting with your hospital team.</p></div>}
        </main>
      </div>
    </section>
  );
}
