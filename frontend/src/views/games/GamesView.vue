<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";

const CATEGORY_LABELS = { company: "Quiz entreprise", event: "Jeu événementiel" };
const CATEGORY_ICONS = { company: "fa-solid fa-building", event: "fa-solid fa-calendar-star" };
const CATEGORY_TONE = { company: "red", event: "navy" };

const quizzes = ref([]);
const loading = ref(true);

const activeQuizId = ref(null);
const questions = ref([]);
const loadingQuestions = ref(false);
const answers = reactive({});
const submitting = ref(false);
const result = ref(null);
const playError = ref("");

async function loadQuizzes() {
  loading.value = true;
  try {
    const { data } = await api.get("/games/");
    quizzes.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function startQuiz(quiz) {
  activeQuizId.value = quiz.id;
  result.value = null;
  playError.value = "";
  Object.keys(answers).forEach((k) => delete answers[k]);
  loadingQuestions.value = true;
  try {
    const { data } = await api.get(`/games/${quiz.id}/questions/`);
    questions.value = data;
  } finally {
    loadingQuestions.value = false;
  }
}

function closeQuiz() {
  activeQuizId.value = null;
  questions.value = [];
  result.value = null;
}

const allAnswered = computed(() => questions.value.length > 0 && questions.value.every((q) => q.id in answers));

async function submitQuiz(quiz) {
  playError.value = "";
  submitting.value = true;
  try {
    const { data } = await api.post(`/games/${quiz.id}/submit/`, { answers });
    result.value = data;
    await loadQuizzes();
  } catch (e) {
    playError.value = e?.response?.data?.detail || "Impossible d'enregistrer votre score.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadQuizzes);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-gamepad" style="color: var(--ie-red); margin-right: 8px;"></i>Jeux</h1>
        <p class="ie-page-subtitle">Testez vos connaissances et tentez le meilleur score !</p>
      </div>
    </div>

    <div v-if="loading" class="ie-games-grid">
      <div v-for="i in 2" :key="i" class="ie-skeleton" style="height: 160px;"></div>
    </div>

    <div v-else-if="quizzes.length" class="ie-games-grid">
      <div v-for="quiz in quizzes" :key="quiz.id" class="ie-card ie-game-card">
        <div class="ie-game-icon" :class="`ie-game-icon-${CATEGORY_TONE[quiz.category] || 'red'}`">
          <i :class="CATEGORY_ICONS[quiz.category] || 'fa-solid fa-gamepad'"></i>
        </div>
        <div class="ie-game-body">
          <span class="ie-game-eyebrow">{{ CATEGORY_LABELS[quiz.category] || quiz.category }}</span>
          <h3 class="ie-game-title">{{ quiz.title }}</h3>
          <p class="ie-game-desc">{{ quiz.description || "Aucune description fournie." }}</p>
          <div class="ie-game-meta">
            <span><i class="fa-solid fa-list-check"></i> {{ quiz.question_count }} question(s)</span>
            <span v-if="quiz.best_score"><i class="fa-solid fa-trophy"></i> Meilleur score : {{ quiz.best_score.score }}/{{ quiz.best_score.total_questions }} ({{ quiz.best_score.percent }}%)</span>
          </div>
          <button class="ie-btn ie-btn-primary" style="width: 100%; margin-top: 10px;" @click="startQuiz(quiz)">
            <i class="fa-solid fa-play"></i> Jouer
          </button>
        </div>
      </div>
    </div>
    <EmptyState v-else icon="fa-solid fa-gamepad" text="Aucun jeu disponible pour le moment." />

    <div v-if="activeQuizId" class="ie-quiz-overlay" @click.self="closeQuiz">
      <div class="ie-quiz-modal">
        <button class="ie-quiz-close" @click="closeQuiz"><i class="fa-solid fa-xmark"></i></button>

        <template v-if="loadingQuestions">
          <div class="ie-skeleton" style="height: 40px; margin-bottom: 12px;" v-for="i in 3" :key="i"></div>
        </template>

        <template v-else-if="result">
          <div class="ie-quiz-result">
            <div class="ie-quiz-score">{{ result.attempt.score }} / {{ result.attempt.total_questions }}</div>
            <p class="ie-quiz-percent">{{ result.attempt.percent }}% de bonnes réponses</p>
          </div>
          <div class="ie-quiz-review">
            <div v-for="item in result.review" :key="item.question_id" class="ie-review-question" :class="item.is_correct ? 'correct' : 'incorrect'">
              <p class="ie-review-text"><i :class="item.is_correct ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i> {{ item.text }}</p>
              <p class="ie-review-answer">
                Bonne réponse : <strong>{{ item.choices[item.correct_index] }}</strong>
                <template v-if="!item.is_correct && item.chosen_index !== null && item.chosen_index !== undefined">
                  — votre réponse : {{ item.choices[item.chosen_index] }}
                </template>
              </p>
            </div>
          </div>
          <button class="ie-btn ie-btn-secondary" style="width: 100%; margin-top: 14px;" @click="closeQuiz">Fermer</button>
        </template>

        <template v-else>
          <h2 class="ie-quiz-title">{{ quizzes.find((q) => q.id === activeQuizId)?.title }}</h2>
          <div class="ie-quiz-questions">
            <div v-for="(q, i) in questions" :key="q.id" class="ie-quiz-question">
              <p class="ie-quiz-question-text">{{ i + 1 }}. {{ q.text }}</p>
              <label v-for="(choice, idx) in q.choices" :key="idx" class="ie-quiz-choice">
                <input type="radio" :name="`q-${q.id}`" :value="idx" v-model.number="answers[q.id]" />
                {{ choice }}
              </label>
            </div>
          </div>
          <p v-if="playError" class="ie-alert ie-alert-danger">{{ playError }}</p>
          <button
            class="ie-btn ie-btn-primary" style="width: 100%; margin-top: 10px;"
            :disabled="!allAnswered || submitting"
            @click="submitQuiz(quizzes.find((q) => q.id === activeQuizId))"
          >
            {{ submitting ? "Validation…" : "Valider mes réponses" }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-games-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }
.ie-game-card { display: flex; gap: 16px; padding: 20px; }
.ie-game-icon {
  width: 56px; height: 56px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 22px;
}
.ie-game-icon-red { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-game-icon-navy { background: var(--ie-navy-soft); color: var(--ie-navy); }
.ie-game-body { flex: 1; min-width: 0; }
.ie-game-eyebrow { font-size: 10.5px; font-weight: 800; letter-spacing: 0.05em; color: var(--ie-red); text-transform: uppercase; }
.ie-game-title { margin: 4px 0 6px; font-size: 15px; color: var(--ie-navy); }
.ie-game-desc { font-size: 12.5px; color: var(--ie-muted); margin: 0 0 10px; line-height: 1.5; }
.ie-game-meta { display: flex; flex-direction: column; gap: 4px; font-size: 11.5px; color: var(--ie-ink); }
.ie-game-meta i { color: var(--ie-red); width: 14px; }

.ie-quiz-overlay {
  position: fixed; inset: 0; background: rgba(23, 27, 38, 0.55);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px;
}
.ie-quiz-modal {
  background: #fff; border-radius: 14px; padding: 26px; max-width: 560px; width: 100%;
  max-height: 85vh; overflow-y: auto; position: relative;
}
.ie-quiz-close {
  position: absolute; top: 14px; right: 14px; border: 0; background: var(--ie-navy-soft);
  width: 30px; height: 30px; border-radius: 50%; color: var(--ie-navy); cursor: pointer;
}
.ie-quiz-title { margin: 0 0 16px; font-size: 16px; color: var(--ie-navy); padding-right: 30px; }
.ie-quiz-questions { display: flex; flex-direction: column; gap: 16px; }
.ie-quiz-question-text { font-size: 13.5px; font-weight: 700; color: var(--ie-ink); margin: 0 0 8px; }
.ie-quiz-choice {
  display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ie-ink);
  padding: 7px 0; cursor: pointer;
}
.ie-quiz-result { text-align: center; padding: 10px 0 18px; }
.ie-quiz-score { font-size: 34px; font-weight: 900; color: var(--ie-red); }
.ie-quiz-percent { font-size: 13px; color: var(--ie-muted); margin: 4px 0 0; }
.ie-quiz-review { display: flex; flex-direction: column; gap: 10px; }
.ie-review-question { border-radius: 10px; padding: 10px 12px; font-size: 12.5px; }
.ie-review-question.correct { background: var(--ie-success-soft); }
.ie-review-question.incorrect { background: var(--ie-red-soft); }
.ie-review-text { margin: 0 0 4px; font-weight: 600; color: var(--ie-ink); }
.ie-review-text i.fa-circle-check { color: var(--ie-success); margin-right: 6px; }
.ie-review-text i.fa-circle-xmark { color: var(--ie-red); margin-right: 6px; }
.ie-review-answer { margin: 0; color: var(--ie-muted); }
</style>
