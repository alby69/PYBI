import { GridLayout, GridItem } from 'https://cdn.jsdelivr.net/npm/grid-layout-plus@1.1.1/dist/grid-layout-plus.mjs';

export default {
    template: `
        <div class="dashboard-grid-container w-full h-full min-h-[500px]">
            <GridLayout
                v-model:layout="localLayout"
                :col-num="colNum"
                :row-height="rowHeight"
                :is-draggable="isDraggable"
                :is-resizable="isResizable"
                :vertical-compact="true"
                :use-css-transforms="true"
                class="w-full bg-slate-50 border rounded p-2"
                @layout-updated="onLayoutUpdated"
            >
                <GridItem
                    v-for="item in localLayout"
                    :key="item.i"
                    :x="item.x"
                    :y="item.y"
                    :w="item.w"
                    :h="item.h"
                    :i="item.i"
                    :is-draggable="isDraggable"
                    :is-resizable="isResizable"
                    class="bg-white border rounded shadow-sm p-3 flex flex-col justify-between overflow-hidden"
                    @moved="onItemMoved"
                    @resized="onItemResized"
                >
                    <div class="font-semibold text-sm border-b pb-1 mb-2 flex items-center justify-between text-gray-800">
                        <span>{{ item.title || 'Widget ' + item.i }}</span>
                        <span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 uppercase">{{ item.type || 'card' }}</span>
                    </div>

                    <!-- Widget Content Types -->
                    <div class="flex-grow flex items-center justify-center overflow-auto p-1 text-center">
                        <div v-if="item.type === 'kpi'" class="flex flex-col items-center">
                            <span class="text-3xl font-extrabold text-blue-600">{{ item.value || '$124,500' }}</span>
                            <span class="text-xs text-emerald-600 font-medium">{{ item.subtitle || '▲ +12.5% vs last month' }}</span>
                        </div>
                        <div v-else-if="item.type === 'chart'" class="w-full h-full flex flex-col justify-around py-2">
                            <div class="text-xs text-gray-500 mb-1 font-mono">{{ item.chartType || 'Bar Chart' }}</div>
                            <div class="flex items-end justify-center gap-2 h-24 w-full px-4">
                                <div class="bg-blue-500 rounded-t w-6 h-12"></div>
                                <div class="bg-blue-500 rounded-t w-6 h-20"></div>
                                <div class="bg-blue-500 rounded-t w-6 h-16"></div>
                                <div class="bg-blue-500 rounded-t w-6 h-24"></div>
                            </div>
                        </div>
                        <div v-else-if="item.type === 'table'" class="w-full text-xs">
                            <table class="w-full border-collapse">
                                <thead>
                                    <tr class="bg-gray-100 text-gray-700">
                                        <th class="p-1 border text-left">Region</th>
                                        <th class="p-1 border text-right">Revenue</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr><td class="p-1 border text-left">Europe</td><td class="p-1 border text-right">$45,200</td></tr>
                                    <tr><td class="p-1 border text-left">North America</td><td class="p-1 border text-right">$62,100</td></tr>
                                    <tr><td class="p-1 border text-left">Asia Pacific</td><td class="p-1 border text-right">$17,200</td></tr>
                                </tbody>
                            </table>
                        </div>
                        <div v-else class="text-sm text-gray-600">
                            {{ item.content || 'Sample Widget Content' }}
                        </div>
                    </div>

                    <div v-if="isDraggable || isResizable" class="text-[10px] text-gray-400 border-t pt-1 mt-1 text-right font-mono">
                        x:{{ item.x }} y:{{ item.y }} w:{{ item.w }} h:{{ item.h }}
                    </div>
                </GridItem>
            </GridLayout>
        </div>
    `,
    components: {
        GridLayout,
        GridItem
    },
    props: {
        layout: {
            type: Array,
            default: () => []
        },
        colNum: {
            type: Number,
            default: 12
        },
        rowHeight: {
            type: Number,
            default: 60
        },
        isDraggable: {
            type: Boolean,
            default: true
        },
        isResizable: {
            type: Boolean,
            default: true
        }
    },
    data() {
        return {
            localLayout: []
        };
    },
    watch: {
        layout: {
            handler(newVal) {
                this.localLayout = JSON.parse(JSON.stringify(newVal || []));
            },
            deep: true,
            immediate: true
        }
    },
    methods: {
        onLayoutUpdated(newLayout) {
            this.$emit('layout_updated', { layout: newLayout });
            this.$emit('change', { layout: newLayout });
        },
        onItemMoved(i, newX, newY) {
            this.$emit('item_moved', { i, x: newX, y: newY, layout: this.localLayout });
        },
        onItemResized(i, newH, newW, newHPx, newWPx) {
            this.$emit('item_resized', { i, h: newH, w: newW, layout: this.localLayout });
        }
    }
};
