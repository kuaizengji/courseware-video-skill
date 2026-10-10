"""Stacks (example episode) - beat script. id -> (zh caption, English VO).
zh = Chinese explanation caption (bottom). vo = English narration (am_michael), phrased to be speakable:
code tokens are spoken ("plus-plus top", "minus one", "is empty"), never read verbatim.
Content rule: no references to slides/lectures/courseware in any viewer-facing text or VO."""
BEATS = {
 # 00 title
 "t0":  ("栈：后进先出。", "Stacks. Last in, first out."),
 # 01 definition
 "d1":  ("栈是一种特殊的线性表：插入和删除都只发生在同一端。", "A stack is a special kind of list. Insertion and deletion both happen at the same end."),
 "d2":  ("这一端叫栈顶 top，另一端叫栈底 bottom。", "That end is the top. The other end is the bottom."),
 "d3":  ("一切都发生在栈顶，栈底什么也不发生。", "Everything happens at the top. Nothing happens at the bottom."),
 "d4":  ("所以最后放进去的，总是最先出来。", "So the last item in is always the first one out."),
 "d5":  ("这就是 LIFO：后进先出。", "That's why stacks are called LIFO lists. Last in, first out."),
 # 02 operations
 "o1":  ("主要操作：push 和 pop，此外还有 top。", "The primary operations are push and pop, plus top."),
 "o2":  ("push：把元素放到栈顶。", "Push adds an element to the top."),
 "o3":  ("再 push B，B 成为新的栈顶。", "Push B, and B becomes the new top."),
 "o4":  ("pop：移除栈顶元素，并返回它。", "Pop removes the top element, and returns it."),
 "o5":  ("top：只返回栈顶元素，不移除。", "Top returns the top element without removing it."),
 "o6":  ("容量固定时，还需要两个判断：isEmpty 和 isFull。", "With a fixed capacity, we need two checks: is empty, and is full."),
 "o7":  ("空栈时 isEmpty 为 true；装满时 isFull 为 true。", "Is empty is true when nothing is inside. Is full is true once every slot is used."),
 "o8":  ("栈满还 push：失败，返回 null —— 上溢。", "Pushing onto a full stack fails, and returns null. That's overflow."),
 "o9":  ("栈空还 pop 或 top：同样返回 null —— 下溢。", "Popping an empty stack, or asking for its top, also returns null. That's underflow."),
 # 03 applications
 "a1":  ("栈的应用：表达式求值、回溯、内存管理。", "Stacks show up in expression evaluation, in backtracking, and in memory management."),
 # 04 array or linked list
 "c1":  ("回忆：List 为什么通常不用数组实现？栈呢？", "Recall why we usually don't build a list on an array. Does that apply to a stack?"),
 "c2":  ("List 用数组时，中间插入或删除要挪动大量元素。", "For a list, inserting or removing in the middle of an array shifts lots of elements."),
 "c3":  ("栈只在一端操作，不用挪动：push、pop、top 都是 O(1)。", "A stack only works at one end, so nothing shifts. Push, pop and top are constant time either way."),
 "c4":  ("区别在空间：数组容量固定；链表按需增长，但每个结点多一个指针。", "The difference is space. An array has a fixed capacity. A linked list grows on demand, but each node carries an extra pointer."),
 "c5":  ("这里我们用数组来实现。", "Here, we'll use an array."),
 # 05 implementation
 "i1":  ("元素存放在数组 values 中，top 是栈顶元素的下标。", "Elements live in an array called values. Top holds the index of the top element."),
 "i2":  ("Stack 类：两个属性、一个构造函数、六个方法；这里用 Double 演示。", "Here's the Stack class: two fields, a constructor, and six methods. Double is just for demonstration."),
 "i3":  ("构造函数：创建容量为 size 的数组，并令 top = -1。", "The constructor creates an array of the given size, and sets top to minus one."),
 "i4":  ("为什么是 -1？", "Why minus one?"),
 "i5":  ("top 是栈顶元素的下标；空栈没有栈顶，所以 top 停在 0 的下方。", "Top is the index of the top element. An empty stack has no top, so top sits just below index zero."),
 "i6":  ("这样第一个元素正好写入 values[0]，top == -1 即表示栈空。", "Then the first push lands exactly in slot zero, and top equal to minus one simply means empty."),
 "i7":  ("push：先检查是否已满，满了就返回 null。", "Push first checks whether the stack is full. If it is, it returns null."),
 "i8":  ("关键一行 values[++top]：先把 top 加一，再用作下标。", "Then the key line. Plus-plus top is a pre-increment: top goes up by one first, then it's used as the index."),
 "i9":  ("最后返回 top()，也就是刚放入的元素。", "Finally it returns top, the element we just pushed."),
 # 06 displayStack
 "p1":  ("displayStack：从栈顶开始，自上而下打印。", "Display stack prints the stack from the top down."),
 "p2":  ("先用 print 输出 top -->，不换行。", "It starts with the top arrow label, on the same line."),
 "p3":  ("循环从 i = top 到 0，每行一个元素。", "Then the loop runs from top down to zero, one element per line."),
 "p4":  ("格式 %, .4f：四位小数，正数前留空格，与负号对齐。", "The format gives four decimal places, with a space before positive numbers, so they line up with negatives."),
 "p5":  ("最后打印底线，代表栈底。", "A base line marks the bottom."),
 # 07 demo main()
 "m0":  ("现在，一步一步完整追踪一个 main() 程序。", "Now let's trace a complete main program, step by step."),
 "m1":  ("new Stack(4)：容量为 4 的空栈，top = -1。", "A new stack of capacity four. Top is minus one."),
 "m2":  ("isEmpty() 为真，打印 true。", "It's empty, so we print true."),
 "m3":  ("push(-3)，再 push(5)。", "Push minus three, then push five."),
 "m4":  ("打印标题并显示：5 在上，-3 在下。", "After the heading, the display shows five above minus three."),
 "m5":  ("push(1)、push(2)：栈满了，top = 3。", "Push one, and two. Now it's full, and top is three."),
 "m6":  ("push(-1)：栈已满，失败返回 null，栈不变。", "Push minus one fails. The stack is full, so it returns null, and nothing changes."),
 "m7":  ("所以这次显示 4 个元素，没有 -1。", "So the display shows four items, with no minus one."),
 "m8":  ("top() 返回 2.0；拼接进字符串打印为 2.0。", "Top returns two point oh. Joined into a string, it prints as two point oh, not four decimals."),
 "m9":  ("isFull() 为真，打印 true。", "Is full returns true, so we print true."),
 "m10": ("四次 pop：2、1、5、-3 依次离开 —— 后进先出。", "Four pops remove two, one, five, and minus three. Last in, first out."),
 "m11": ("栈空，top 回到 -1；最后只打印 top --> 和底线。", "Top is back to minus one, so the last display is just the arrow and the base line."),
 "m12": ("把它们放在一起，就是 main() 的完整输出。", "Put together, that's the complete output of main."),
 # 08 summary (knowledge points only - no homework/lab/task content, series rule)
 "s1":  ("小结：栈只在栈顶操作，后进先出；push、pop、top，以及 isEmpty、isFull。", "To sum up: a stack works only at the top. Last in, first out. Push, pop and top, plus is empty and is full."),
 "s2":  ("数组实现：top 从 -1 开始，push 用 values[++top]，失败返回 null。", "With an array, top starts at minus one, push pre-increments, and failures return null."),
 "e1":  ("下一集：队列。", "Next up: queues."),
}
