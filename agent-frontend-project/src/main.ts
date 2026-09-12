import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import router from '@/router'
import '@/styles/index.scss'
import App from './App.vue'

const app = createApp(App)

// 全量注册 Element Plus，后续可按需引入优化体积
app.use(ElementPlus)
app.use(createPinia())
app.use(router)

app.mount('#app')
