interface ListOptions {
    sort?: 'recent' | 'name';
    json?: boolean;
}
export declare class ListCommand {
    execute(targetPath?: string, mode?: 'changes' | 'specs', options?: ListOptions): Promise<void>;
}
export {};
//# sourceMappingURL=list.d.ts.map