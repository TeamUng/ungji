import { useEffect, useMemo, useState } from "react";
import { CoachLayer } from "@/components/coach/CoachLayer";
import { LearningActivityPage } from "@/components/learning/LearningActivityPage";
import { TabletFrame } from "@/components/shell/TabletFrame";
import { TodayLearningPage } from "@/components/today/TodayLearningPage";
import { studentCases } from "@/data/mockCases";
import { useChatSession } from "@/hooks/useChatSession";
import { useCoachLayer } from "@/hooks/useCoachLayer";
import type { ChoiceItem, Touchpoint } from "@/types/chat";
import type { CaseId } from "@/types/learning";

type AppView = "today" | "learning";

function App() {
  const [caseId, setCaseId] = useState<CaseId>("case2");
  const [view, setView] = useState<AppView>("today");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const activeCase = studentCases[caseId];
  const selectedTask = useMemo(() => {
    const taskId = selectedTaskId ?? activeCase.recommendedTaskId;
    return activeCase.todayTasks.find((task) => task.id === taskId) ?? activeCase.todayTasks[0];
  }, [activeCase, selectedTaskId]);

  const chat = useChatSession(activeCase);
  const coachLayer = useCoachLayer();

  useEffect(() => {
    setView("today");
    setSelectedTaskId(null);
    coachLayer.showFloating("tp1");
    void chat.startTouchpoint("tp1", "talk");
  }, [activeCase.id]);

  function startTask(taskId: string) {
    setSelectedTaskId(taskId);
    setView("learning");
    coachLayer.hide();
    chat.clearMessages();
  }

  function showTalkTouchpoint(touchpoint: Touchpoint) {
    coachLayer.showFloating(touchpoint);
    void chat.startTouchpoint(touchpoint, "talk");
  }

  function openLearningHelp() {
    coachLayer.openDrawer("tp4");
    void chat.startTouchpoint("tp4", "learning");
  }

  function handleCaseChange(nextCaseId: CaseId) {
    setCaseId(nextCaseId);
  }

  function handleCoachChoice(choice: ChoiceItem) {
    if (choice.id.startsWith("start:")) {
      startTask(choice.id.replace("start:", ""));
      return;
    }

    if (choice.id === "open-help") {
      openLearningHelp();
      return;
    }

    if (choice.id === "finish-day") {
      showTalkTouchpoint("tp5");
      return;
    }

    void chat.sendChoice(choice);
  }

  function handleSendText(content: string) {
    void chat.sendText(content);
  }

  return (
    <main className="min-h-screen bg-[#eef3f8] px-4 py-5 text-slate-950 sm:px-6 lg:px-8">
      <section className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl items-center justify-center">
        <TabletFrame activeCaseId={caseId} onCaseChange={handleCaseChange}>
          <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-[#f9e78e]">
            {view === "today" ? (
              <TodayLearningPage
                studentCase={activeCase}
                onStartTask={startTask}
                onShowTouchpoint={showTalkTouchpoint}
              />
            ) : (
              <LearningActivityPage
                studentCase={activeCase}
                task={selectedTask}
                onBackToday={() => {
                  setView("today");
                  showTalkTouchpoint("tp2");
                }}
                onCompleteTask={() => {
                  setView("today");
                  showTalkTouchpoint("tp2");
                }}
                onExitAttempt={() => showTalkTouchpoint("tp3")}
                onFinishDay={() => showTalkTouchpoint("tp5")}
              />
            )}

            <CoachLayer
              surface={coachLayer.surface}
              touchpoint={coachLayer.touchpoint}
              messages={chat.messages}
              isLoading={chat.isLoading}
              onAvatarClick={view === "learning" ? openLearningHelp : undefined}
              onClose={coachLayer.hide}
              onChoice={handleCoachChoice}
              onSendText={handleSendText}
            />
          </div>
        </TabletFrame>
      </section>
    </main>
  );
}

export default App;
