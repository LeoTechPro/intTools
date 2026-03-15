export declare class ArchiveCommand {
    execute(changeName?: string, options?: {
        yes?: boolean;
        skipSpecs?: boolean;
        noValidate?: boolean;
        validate?: boolean;
    }): Promise<void>;
    private selectChange;
    private getArchiveDate;
}
//# sourceMappingURL=archive.d.ts.map